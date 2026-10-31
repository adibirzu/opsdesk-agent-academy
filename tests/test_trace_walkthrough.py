import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_workshop.cli import main
from agent_workshop.trace_walkthrough import summarize_events

TRACE = '1' * 32


class TraceWalkthroughTests(unittest.TestCase):
    def record(self, directory, rows):
        path = Path(directory) / 'events.jsonl'
        path.write_text(''.join(json.dumps({'trace_id': TRACE, 'session.id': 'lesson', **row})+'\n' for row in rows))
        return path

    def test_exact_selection_content_exclusion_and_evidence_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.record(directory, [
                {'event':'run.start', 'prompt':'do-not-display'},
                {'event':'llm.usage','input_tokens':100,'output_tokens':20,'estimated_cost_usd':0.001,'cost_basis':'configured_uncached_text_rates','model':'secret-model-name'},
                {'event':'tool.start','tool':'secret-resource-name','arguments':{'key':'do-not-display'}},
                {'event':'tool.end','result':'do-not-display'},
                {'event':'run.end','status':'success','answer':'do-not-display'},
                {'event':'run.end','status':'failure','trace_id':'2'*32},
                {'event':'run.end','status':'failure','session.id':'other'},
                {'event':'untrusted-secret-event-name','provider_verified':True}])
            report = summarize_events(path, TRACE, 'lesson')
            self.assertEqual(report['outcome'], 'success')
            self.assertEqual(report['usage']['input_tokens'],100)
            self.assertEqual(report['estimated_cost_usd'],.001)
            self.assertFalse(report['provider_verified'])
            self.assertEqual(report['evidence_class'],'local_record_only')
            self.assertEqual(report['unknown_event_count'],1)
            encoded = json.dumps(report)
            for value in ('do-not-display','secret-model-name','secret-resource-name','untrusted-secret-event-name',TRACE,'lesson'):
                self.assertNotIn(value,encoded)

    def test_partial_usage_retains_lower_bound_without_inventing_total(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.record(directory,[{'event':'llm.usage','input_tokens':None,'output_tokens':9},
                {'event':'llm.usage','input_tokens':20,'output_tokens':3}])
            report=summarize_events(path,TRACE,'lesson')
            self.assertEqual(report['outcome'],'incomplete')
            self.assertIsNone(report['usage']['input_tokens'])
            self.assertIsNone(report['usage']['output_tokens'])
            self.assertEqual(report['usage']['known_token_lower_bound'],32)
            self.assertIsNone(report['estimated_cost_usd'])

    def test_policy_and_failure_walkthrough_is_not_reexecuted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.record(directory,[{'event':'security.decision','decision':'approval_required'},
                {'event':'tool.error','error':'private exception'}, {'event':'run.end','status':'failure'}])
            report=summarize_events(path,TRACE,'lesson')
            self.assertEqual(report['outcome'],'failure')
            self.assertEqual([r['stage'] for r in report['timeline']],['security','failure','completion'])
            self.assertNotIn('private exception',json.dumps(report))

    def test_graph_approval_gate_has_no_model_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.record(directory,[{'event':'security.decision','decision':'approval_required'},
                {'event':'coordinator.end','status':'approval_required'}])
            report=summarize_events(path,TRACE,'lesson')
            self.assertEqual(report['outcome'],'approval_required')
            self.assertIsNone(report['usage']['input_tokens'])
            self.assertIsNone(report['estimated_cost_usd'])
            self.assertNotIn('model',[r['stage'] for r in report['timeline']])

    def test_cli_requires_no_config_model_or_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.record(directory,[{'event':'run.end','status':'success'}]);output=io.StringIO()
            with patch('agent_workshop.cli.load',side_effect=AssertionError('no config reads')), \
                    patch('agent_workshop.cli.live_model',side_effect=AssertionError('no inference')), \
                    contextlib.redirect_stdout(output):
                code=main(['explain','--events',str(path),'--trace',TRACE,'--session','lesson'])
            self.assertEqual(code,0)
            self.assertFalse(json.loads(output.getvalue())['provider_verified'])

    def test_invalid_duplicate_json_and_ambiguous_runs_fail(self):
        for content in ('[]\n','{"trace_id":"x","trace_id":"y"}\n','{"n":NaN}\n','broken\n'):
            with self.subTest(content=content),tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'events';path.write_text(content)
                with self.assertRaises(ValueError):summarize_events(path,TRACE,'lesson')
        with tempfile.TemporaryDirectory() as directory:
            path=self.record(directory,[{'event':'run.end','status':'success'},{'event':'run.end','status':'failure'}])
            with self.assertRaises(ValueError):summarize_events(path,TRACE,'lesson')

    def test_file_and_selection_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.record(directory,[{'event':'run.start'}]);link=Path(directory)/'link';link.symlink_to(path)
            for source,trace,session in ((link,TRACE,'lesson'),(path,'invalid','lesson'),(path,TRACE,'bad\nsession'),(path,'2'*32,'lesson')):
                with self.assertRaises(ValueError):summarize_events(source,trace,session)
            path.write_bytes(b' '*1_000_001)
            with self.assertRaises(ValueError):summarize_events(path,TRACE,'lesson')
            path=self.record(directory,[{'event':'step.start'}]*501)
            with self.assertRaises(ValueError):summarize_events(path,TRACE,'lesson')

    def test_invalid_usage_does_not_become_free_or_known(self):
        for value in (True,-1,1.5,'secret'):
            with self.subTest(value=value),tempfile.TemporaryDirectory() as directory:
                path=self.record(directory,[{'event':'llm.usage','input_tokens':value,'output_tokens':3}])
                with self.assertRaises(ValueError):summarize_events(path,TRACE,'lesson')
