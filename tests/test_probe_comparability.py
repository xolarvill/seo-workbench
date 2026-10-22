from seo_workbench_tools.headless import _first_rendered_view, compare_page


def test_failed_desktop_does_not_silently_use_mobile_content():
    assert _first_rendered_view({'viewports': {'desktop_1920x1080': {'error': 'crashed'}, 'mobile_375x812': {'title': 'Mobile'}}}) == {}


def test_different_final_routes_cannot_prove_metadata_mismatch():
    result = compare_page({'url': 'https://example.com/a', 'canonical': 'https://example.com/a'}, {'url': 'https://example.com/b', 'canonical': 'https://example.com/b'})
    assert result['diffs'] == []
    assert result['comparison_status'] == 'different_final_url'


def test_challenge_or_partial_dom_cannot_prove_missing_elements():
    result = compare_page({'url': 'https://example.com/a', 'h1': ['Real']}, {'url': 'https://example.com/a', 'h1': [], 'comparison_eligible': False})
    assert result['diffs'] == []
    assert result['comparison_status'] == 'rendered_evidence_unavailable'


def test_nonroot_trailing_slash_is_a_different_route():
    result=compare_page({'url':'https://example.com/a','canonical':'one'}, {'url':'https://example.com/a/','canonical':'two'})
    assert result['diffs']==[] and result['comparison_status']=='different_final_url'


def test_partial_rendered_collection_marks_bundle_partial(tmp_path, monkeypatch):
    from seo_workbench_tools import evidence_bundle, rendered_probe
    monkeypatch.setattr(evidence_bundle.page_probe,'probe',lambda *_args,**_kwargs:{'url':'https://example.com/','status':200,'evidence_quality':{'html_eligible':True}})
    monkeypatch.setattr(evidence_bundle.robots_sitemap_probe,'probe',lambda *_args,**_kwargs:{})
    monkeypatch.setattr(rendered_probe,'capture',lambda *_args,**_kwargs:{'pages':[],'collection_status':'failed'})
    bundle=evidence_bundle.collect('https://example.com/',[],1,1,rendered=True,rendered_output_dir=tmp_path,crawl_limit=0)
    assert bundle['collection_status']=='partial'
    assert bundle['source_confidence']['rendered_dom']==0


def test_technical_consumer_cannot_fill_raw_missing_h1_from_incomparable_render(tmp_path, monkeypatch):
    from seo_workbench import state,tech_audit as audit
    from seo_workbench_tools import rendered_probe
    root=tmp_path/'project';state.init_state('general','Example','https://example.com/',project_dir=root)
    async def fetch(url,*_):
        return {'status':200,'final_url':url,'headers':{'content-type':'text/html'},'body':b'<title>Page</title>'}
    monkeypatch.setattr(audit,'_fetch',fetch)
    monkeypatch.setattr(rendered_probe,'capture',lambda *_a,**_k:{'pages':[{'url':'https://example.com/','viewports':{'desktop_1920x1080':{'url':'https://example.com/different','h1':['Other page'],'comparison_eligible':True}}}]})
    audit.run_tech_audit(root,audit.CrawlConfig(load_sitemap=False,rendered=True,request_delay=0))
    assert any(i['rule_id']=='MISSING_H1' for i in audit.load_tech_issues(root))
