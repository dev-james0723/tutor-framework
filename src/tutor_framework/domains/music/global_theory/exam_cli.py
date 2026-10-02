"""Local exact-resource exam operations; requests do not authorize network implicitly."""
from __future__ import annotations
from pathlib import Path
from .exam import ExamStore, PurposeGrant
from .mineru_adapter import ExistingMinerUResult, ExistingMinerUHelper


def execute_exam_request(request: dict, *, no_save: bool = False) -> dict:
    if type(no_save) is not bool:
        raise ValueError('no-save requires a boolean')
    if no_save and request.get('storage_root'):
        raise ValueError('no-save forbids a persistent exam bank')
    store = ExamStore(request['catalogue'], tenant_id=request['tenant_id'], no_save=no_save,
                      storage_root=Path(request['storage_root']) if request.get('storage_root') else None)
    action = request['action']; parameters = dict(request.get('parameters', {}))
    if action == 'retrieve':
        return {'questions':store.retrieve(**parameters)}
    if action == 'tutor':
        return store.tutor(**parameters)
    if action == 'finish_exam':
        return store.finish_exam(**parameters)
    if action == 'finish_practice':
        return store.finish_practice(**parameters)
    if action == 'add_answer_layer':
        return store.add_layer(**parameters)
    grant_data = dict(request['grant'])
    grant_data['resource_ids'] = tuple(grant_data['resource_ids'])
    grant = PurposeGrant(**grant_data)
    if action == 'match_official_answer':
        answer_file = Path(parameters.pop('answer_pdf')).expanduser()
        if answer_file.stat().st_size > 100_000_000:
            raise ValueError('answer PDF exceeds pilot size')
        return store.match_official_answer(grant=grant, answer_bytes=answer_file.read_bytes(), **parameters)
    if action != 'ingest':
        raise ValueError('unsupported exam action')
    resource_id = parameters['resource_id']
    original = Path(parameters['original_pdf']).expanduser()
    if original.stat().st_size > 100_000_000:
        raise ValueError('original PDF exceeds pilot size')
    digest = request['catalogue'][resource_id]['sha256']
    parser = parameters['parser']
    if parser['kind'] == 'existing_result':
        adapter = ExistingMinerUResult(resource_id, Path(parser['result_directory']), digest)
    elif parser['kind'] == 'existing_helper':
        adapter = ExistingMinerUHelper(resource_id, original, Path(parser['output_directory']), digest,
                                        parser.get('cloud_processing_authorized', False),
                                        parser.get('cost_authorized', False), no_save,
                                        request['catalogue'][resource_id]['language'])
    else:
        raise ValueError('only the existing MinerU integration is supported')
    result = store.ingest(resource_id, original.read_bytes(), grant, adapter)
    return {'paper':result,'new_api_submission':parser['kind']=='existing_helper'}
