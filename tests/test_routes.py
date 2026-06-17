import tempfile
import pytest
from app import app, init_db


@pytest.fixture
def client():
    db = tempfile.NamedTemporaryFile(delete=False)

    app.config['TESTING'] = True
    app.config['DATABASE'] = db.name

    with app.app_context():
        init_db()

    with app.test_client() as client:
        yield client


def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200


def test_assessment_page(client):
    response = client.get('/assessment')
    assert response.status_code == 200


def test_history_page(client):
    response = client.get('/history')
    assert response.status_code == 200
    assert b"Saved Reports" in response.data


def test_result_without_session_redirects(client):
    response = client.get('/result')
    assert response.status_code == 302

def test_result_generation(client):
    response = client.post('/result', data={
        'question_0': 'Walk',
        'question_1': '< 5 kWh',
        'question_2': 'Vegan',
        'question_3': '0 flights',
        'question_4': 'Biomass / Solar',
        'question_5': 'Almost Never',
        'question_6': 'Very Little',
        'question_7': 'Everything',
        'question_8': 'Conscious Saving'
    })

    assert response.status_code == 200
    assert b"ECO SCORE" in response.data
    assert b"ANNUAL EMISSIONS" in response.data

def test_save_report_flow(client):
    client.post('/result', data={
        'question_0': 'Walk',
        'question_1': '< 5 kWh',
        'question_2': 'Vegan',
        'question_3': '0 flights',
        'question_4': 'Biomass / Solar',
        'question_5': 'Almost Never',
        'question_6': 'Very Little',
        'question_7': 'Everything',
        'question_8': 'Conscious Saving'
    })

    response = client.post('/save_report', follow_redirects=True)
    assert response.status_code == 200