from siebel.maintenance.crash import fix_thread_id


def test_fix_thread_id():
    fdr_thread = '2658139040'  # always read as text
    assert fix_thread_id(fdr_thread) == '-1636828256'
