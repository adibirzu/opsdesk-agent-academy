import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import oci
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import hosted_control as h

class HostedReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'deployment.json'
        self.binding={'deployment_id':'dep','hosted_application_id':'app','artifact_digest':'sha256:'+'a'*64,'image_tag':'tag'}
        self.path.write_text(json.dumps(self.binding));self.path.chmod(0o600);self.before=self.path.read_bytes()
        self.state={'compartment_id':'child','object_storage_namespace':'syntheticns','outputs':{k:{'value':v} for k,v in {'hosted_application_id':'app','container_repository_id':'repo','container_repository_name':'workshop/agent'}.items()}}
        self.receipt={'region':'eu-frankfurt-1','tenancy_id':'tenant'};self.args=NS(deployment_receipt=str(self.path))
        self.app=NS(id='app',compartment_id='child',lifecycle_state='ACTIVE')
        self.dep=NS(id='dep',hosted_application_id='app',compartment_id='child',lifecycle_state='ACTIVE',active_artifact=NS(status='ACTIVE',tag='tag',container_uri='eu-frankfurt-1.ocir.io/syntheticns/workshop/agent'))
        self.client=NS(get_hosted_application=lambda _:NS(data=self.app),get_hosted_deployment=lambda _:NS(data=self.dep))
    def tearDown(self):self.tmp.cleanup()
    def check(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out),patch.object(h,'_image') as image:
            code=h._status(self.args,self.state,self.receipt,(self.client,None))
        self.assertEqual(self.path.read_bytes(),self.before,'Status must not rewrite deployment evidence')
        return code,json.loads(out.getvalue()),image
    def test_active_artifact_is_only_eligible_for_canary(self):
        code,report,image=self.check();self.assertEqual(code,0);self.assertEqual(report['readiness'],'ready_for_canary');self.assertIs(report['runtime_verified'],False);image.assert_called_once()
    def test_404_does_not_prove_deleted_or_recreate(self):
        def unavailable(_):raise oci.exceptions.ServiceError(404,'NotAuthorizedOrNotFound',{},'private endpoint and credentials must not appear')
        self.client.get_hosted_application=unavailable
        code,report,image=self.check();self.assertEqual(code,2);self.assertEqual(report['readiness'],'unavailable');self.assertEqual(report['reason'],'not_authorized_or_not_found');self.assertNotIn('private',json.dumps(report));image.assert_not_called()
    def test_foreign_receipt_fails_before_any_provider_call(self):
        self.binding['hosted_application_id']='other';self.path.write_text(json.dumps(self.binding));self.before=self.path.read_bytes()
        self.client.get_hosted_application=lambda _:self.fail('Foreign binding contacted')
        with self.assertRaises(ValueError):self.check()
    def test_inactive_deployment_is_not_ready(self):
        self.dep.lifecycle_state='INACTIVE';code,report,image=self.check();self.assertEqual(code,2);self.assertEqual(report['readiness'],'not_ready');image.assert_not_called()
    def test_inactive_artifact_is_not_ready(self):
        self.dep.active_artifact.status='INACTIVE';code,report,image=self.check();self.assertEqual(code,2);self.assertEqual(report['readiness'],'not_ready');image.assert_not_called()
    def test_pending_requested_artifact_cannot_accept_old_active_one(self):
        self.binding.update(requested_artifact_digest='sha256:'+'b'*64,requested_image_tag='new-tag');self.path.write_text(json.dumps(self.binding));self.before=self.path.read_bytes()
        code,report,image=self.check();self.assertEqual(code,2);self.assertEqual(report['reason'],'active_artifact_differs');image.assert_not_called()
    def test_registry_digest_mismatch_is_not_ready(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out),patch.object(h,'_image',side_effect=ValueError('private mismatch')):
            code=h._status(self.args,self.state,self.receipt,(self.client,None))
        self.assertEqual(code,2);self.assertEqual(json.loads(out.getvalue())['reason'],'artifact_binding_unverified');self.assertEqual(self.path.read_bytes(),self.before)
    def test_foreign_live_deployment_is_rejected(self):
        self.dep.hosted_application_id='other'
        with self.assertRaises(ValueError):self.check()

    def test_iam_application_uses_iam_specific_api(self):
        self.client.get_hosted_application_iam=lambda _:NS(data=self.app)
        self.client.get_hosted_application=lambda _:self.fail('General application API contacted')
        code,report,image=self.check();self.assertEqual(code,0);self.assertEqual(report['readiness'],'ready_for_canary')
    def test_iam_404_does_not_downgrade_to_general_application_api(self):
        def unavailable(_):raise oci.exceptions.ServiceError(404,'NotAuthorizedOrNotFound',{},'private detail')
        self.client.get_hosted_application_iam=unavailable
        self.client.get_hosted_application=lambda _:self.fail('IAM failure bypassed')
        code,report,image=self.check();self.assertEqual(code,2);self.assertEqual(report['readiness'],'unavailable');image.assert_not_called()
