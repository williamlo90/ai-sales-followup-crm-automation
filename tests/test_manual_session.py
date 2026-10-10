import pytest
from scripts.manual_session import Recorder


def test_observed_intervals_and_counts_are_separate():
    now=[0.];r=Recorder(lambda:now[0])
    now[0]=2;r.event('touch')
    now[0]=3;r.event('wait')
    now[0]=8;r.event('work')
    now[0]=9;r.event('correction')
    now[0]=10;result=r.event('done')
    assert result['active_seconds']==5 and result['waiting_seconds']==5
    assert result['touches']==1 and result['corrections']==1
    assert result['completed'] and result['correctness']=='unreviewed'
    with pytest.raises(ValueError,match='ended'):r.event('done')


def test_invalid_transition_does_not_record_a_result():
    now=[0.];r=Recorder(lambda:now[0])
    with pytest.raises(ValueError,match='Already working'):r.event('work')
    assert not r.events
    now[0]=1;result=r.event('abort')
    assert not result['completed']
