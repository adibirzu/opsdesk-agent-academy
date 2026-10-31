#!/usr/bin/env python3
"""Private-receipt OCI Resource Manager lifecycle. No implicit apply or destroy."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys


def private_json(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_mode & 0o077:
        raise ValueError('Private input must be a regular mode-0600 file')
    return json.loads(p.read_text())


def save(path, value):
    p=Path(path);p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if p.is_symlink(): raise ValueError('Receipt symlink refused')
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2)
    p.chmod(0o600)


def flat_variables(values):
    # These are local admission metadata, not Terraform variables.
    excluded={'profile','tenancy_name','shape','stack_kind'}
    if values.get('stack_kind') in {'enterprise', 'oke-iam'}:
        excluded.update({'tenancy_ocid','parent_compartment_ocid','retention_days'})
    return {k: v if isinstance(v,str) else json.dumps(v,separators=(',',':'))
            for k,v in values.items() if k not in excluded}


def admission(values, profile, config, oci):
    from preflight import run_preflight, prove_membership
    identity=oci.identity.IdentityClient(config,timeout=(5,15),retry_strategy=oci.retry.NoneRetryStrategy())
    if values.get('stack_kind') not in {'enterprise', 'oke-iam'}:
        return run_preflight(values,profile,config,{'identity':identity,'compute':oci.core.ComputeClient(config)})
    if values['compartment_ocid']!=values['parent_compartment_ocid']:
        raise ValueError('Runtime stack must reside in its dedicated compartment')
    if identity.get_tenancy(config['tenancy']).data.name!=values['tenancy_name']:
        raise ValueError('Tenancy name mismatch')
    if not prove_membership(identity,values['compartment_ocid'],config['tenancy']):
        raise ValueError('Compartment membership mismatch')
    if values.get('stack_kind') == 'oke-iam':
        cluster = oci.container_engine.ContainerEngineClient(config,timeout=(5,15),
            retry_strategy=oci.retry.NoneRetryStrategy()).get_cluster(values['cluster_id']).data
        if cluster.lifecycle_state != 'ACTIVE' or cluster.type != 'ENHANCED_CLUSTER':
            raise ValueError('Workload identity requires an active enhanced cluster')
        if not prove_membership(identity,cluster.compartment_id,config['tenancy']):
            raise ValueError('Cluster ownership mismatch')
        return {'status':'passed','membership':'passed','enhanced_cluster_owner':'passed'}
    network=oci.core.VirtualNetworkClient(config,timeout=(5,15),retry_strategy=oci.retry.NoneRetryStrategy())
    if network.get_vcn(values['vcn_id']).data.compartment_id!=values['compartment_ocid']:
        raise ValueError('VCN compartment mismatch')
    return {'status':'passed','membership':'passed','vcn_owner':'passed'}


def model_state(data):
    return getattr(data,'lifecycle_state','UNKNOWN')


def response_bytes(response):
    value=response.data
    if isinstance(value,str):return value.encode()
    if isinstance(value,bytes):return value
    content=getattr(value,'content',None)
    if isinstance(content,bytes):return content
    raise ValueError('Unexpected provider response body')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['create','update','plan','status','apply','outputs'])
    p.add_argument('--receipt',required=True)
    p.add_argument('--vars',required=True)
    p.add_argument('--archive')
    p.add_argument('--profile',default='DEFAULT')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--reviewed-plan-sha256')
    a=p.parse_args(argv)
    try:
        values=private_json(a.vars)
        import oci
        c=oci.config.from_file(profile_name=a.profile)
        if c['tenancy']!=values['tenancy_ocid'] or c['region']!=values['region']:
            raise ValueError('OCI target differs from private inputs')
        if values.get('profile',a.profile)!=a.profile:raise ValueError('Profile mismatch')
        r=oci.resource_manager.ResourceManagerClient(c,timeout=(5,30),retry_strategy=oci.retry.NoneRetryStrategy())
        if not a.execute:
            print(json.dumps({'action':a.action,'dry_run':True,'mutation_performed':False}));return 0
        if a.action=='create':
            if Path(a.receipt).exists():raise ValueError('Receipt already exists; inspect existing stack')
            summary=admission(values,a.profile,c,oci)
            archive=Path(a.archive or '')
            if archive.is_symlink() or not archive.is_file():raise ValueError('Regular stack archive required')
            payload=archive.read_bytes()
            if len(payload)>5000000:raise ValueError('Stack archive exceeds bound')
            source=oci.resource_manager.models.CreateZipUploadConfigSourceDetails(config_source_type='ZIP_UPLOAD',zip_file_base64_encoded=base64.b64encode(payload).decode())
            result=r.create_stack(oci.resource_manager.models.CreateStackDetails(
                compartment_id=values['parent_compartment_ocid'],display_name=values.get('prefix','agent-workshop')+'-stack',
                description='Replicable agent operations workshop; dedicated sandbox.',
                config_source=source,variables=flat_variables(values),terraform_version='1.5.x')).data
            now=datetime.now(timezone.utc)
            receipt={'stack_id':result.id,'region':c['region'],'tenancy_id':c['tenancy'],
                'archive_sha256':hashlib.sha256(payload).hexdigest(),
                'variables_sha256':hashlib.sha256(json.dumps(flat_variables(values),sort_keys=True).encode()).hexdigest(),
                'created_at':now.isoformat(),'expires_at':(now+timedelta(days=values['retention_days'])).isoformat(),
                'preflight':summary}
            if values.get('stack_kind') in {'enterprise', 'oke-iam'}:
                receipt['compartment_id']=values['compartment_ocid']
            save(a.receipt,receipt)
            print(json.dumps({'stack':'created','state':model_state(result),'receipt':'saved_privately'}));return 0
        receipt=private_json(a.receipt)
        if receipt['region']!=c['region'] or receipt['tenancy_id']!=c['tenancy']:raise ValueError('Receipt target mismatch')
        current=r.get_stack(receipt['stack_id']).data
        if current.compartment_id!=values['parent_compartment_ocid']:raise ValueError('Stack parent mismatch')
        expected=hashlib.sha256(json.dumps(flat_variables(values),sort_keys=True).encode()).hexdigest()
        if expected!=receipt['variables_sha256'] and a.action!='update':raise ValueError('Variable inputs changed; require a new reviewed stack revision')
        if a.action=='update':
            admission(values,a.profile,c,oci)
            if receipt.get('active_job_id') and model_state(r.get_job(receipt['active_job_id']).data) not in {'SUCCEEDED','FAILED','CANCELED'}:
                raise ValueError('A job is already active')
            archive=Path(a.archive or '')
            if archive.is_symlink() or not archive.is_file():raise ValueError('Regular stack archive required')
            payload=archive.read_bytes()
            if len(payload)>5000000:raise ValueError('Stack archive exceeds bound')
            source=oci.resource_manager.models.UpdateZipUploadConfigSourceDetails(config_source_type='ZIP_UPLOAD',zip_file_base64_encoded=base64.b64encode(payload).decode())
            r.update_stack(receipt['stack_id'],oci.resource_manager.models.UpdateStackDetails(config_source=source,variables=flat_variables(values)))
            receipt['archive_sha256']=hashlib.sha256(payload).hexdigest()
            receipt['variables_sha256']=expected
            for key in ('active_job_id','plan_job_id','apply_job_id'):receipt.pop(key,None)
            save(a.receipt,receipt)
            print(json.dumps({'stack':'updated','plan_review':'required_again'}));return 0
        if a.action=='plan':
            if receipt.get('active_job_id'):
                old=r.get_job(receipt['active_job_id']).data
                if model_state(old) not in {'SUCCEEDED','FAILED','CANCELED'}:raise ValueError('A job is already active')
            job=r.create_job(oci.resource_manager.models.CreateJobDetails(stack_id=receipt['stack_id'],display_name='workshop-plan',operation='PLAN',job_operation_details=oci.resource_manager.models.CreatePlanJobOperationDetails(operation='PLAN'))).data
            receipt.update(plan_job_id=job.id,active_job_id=job.id)
            save(a.receipt,receipt);print(json.dumps({'plan':'submitted','state':model_state(job)}));return 0
        if a.action=='apply':
            if not re.fullmatch(r'[0-9a-f]{64}',a.reviewed_plan_sha256 or ''):raise ValueError('Reviewed plan log SHA-256 required')
            job=r.get_job(receipt['plan_job_id']).data
            if model_state(job)!='SUCCEEDED':raise ValueError('Plan job has not succeeded')
            raw=response_bytes(r.get_job_logs_content(job.id))
            if hashlib.sha256(raw).hexdigest()!=a.reviewed_plan_sha256:raise ValueError('Reviewed plan log digest mismatch')
            applied=r.create_job(oci.resource_manager.models.CreateJobDetails(stack_id=receipt['stack_id'],display_name='workshop-apply',operation='APPLY',job_operation_details=oci.resource_manager.models.CreateApplyJobOperationDetails(operation='APPLY',execution_plan_strategy='FROM_PLAN_JOB_ID',execution_plan_job_id=job.id))).data
            receipt.update(apply_job_id=applied.id,active_job_id=applied.id)
            save(a.receipt,receipt);print(json.dumps({'apply':'submitted','state':model_state(applied)}));return 0
        if a.action=='outputs':
            job=r.get_job(receipt['apply_job_id']).data
            if model_state(job)!='SUCCEEDED':raise ValueError('Apply job has not succeeded')
            raw=response_bytes(r.get_stack_tf_state(receipt['stack_id']))
            target=Path(a.receipt).parent/'orm-state.json'
            save(target,json.loads(raw))
            print(json.dumps({'outputs':'saved_privately','apply':'SUCCEEDED'}));return 0
        if not receipt.get('active_job_id'):
            print(json.dumps({'stack_state':model_state(current),'job_state':'none'}));return 0
        job=r.get_job(receipt['active_job_id']).data
        report={'job_state':model_state(job),'operation':job.operation}
        if report['job_state'] in {'SUCCEEDED','FAILED','CANCELED'}:
            raw=response_bytes(r.get_job_logs_content(job.id))
            target=Path(a.receipt).parent/('orm-'+job.operation.lower()+'.log')
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'wb') as f:f.write(raw)
            report['logs']='saved_privately';report['logs_sha256']=hashlib.sha256(raw).hexdigest()
        print(json.dumps(report));return 0 if report['job_state']!='FAILED' else 1
    except Exception as exc:
        import traceback
        diagnostic=Path(a.receipt).parent/'orm-diagnostic.txt'
        if diagnostic.parent.is_dir() and not diagnostic.is_symlink():
            fd=os.open(diagnostic,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w') as out:out.write(traceback.format_exc())
        print(json.dumps({'status':'failed','error_type':type(exc).__name__,'detail':'Inspect private configuration and provider diagnostics; no fallback action taken'}),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
