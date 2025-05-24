"""Unit Tests Module main"""

import os
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../src')
import pytest

from grosserratwrapper.grosserrat.main import GrosserRat


@pytest.fixture
def cols_members():
    cols_members = {
        'memberid': int,
        'memberFirstName': str,
        'memberLastName': str,
        'memberParty': str,
        'memberDistrict': str,
    }
    return cols_members




@pytest.fixture(scope="class")
def temp_directory(request, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(request.param)
    yield tmp_path
    shutil.rmtree(tmp_path)

class TestGrosserRat:
    pass

class TestInit(TestGrosserRat):
    @classmethod
    def setup_class(cls):
        cls.grosserrat = GrosserRat()

    @classmethod
    def teardown_class(cls):
        del cls.grosserrat

    def test_init_db_path(self):
        assert self.grosserrat.db_path == 'db'

    def test_init_members_dataframe(self):
        assert isinstance(self.grosserrat.members, pd.DataFrame)


class TestCreateDatabase(TestGrosserRat):


    @pytest.mark.integration
    @pytest.mark.parametrize('temp_directory', ['db'], indirect=True)
    def test_db_file_created(self, temp_directory):
        parl = GrosserRat(db_path=Path(temp_directory))
        parl.create_database()
        assert Path(temp_directory, 'grossrat.sqlite3').exists()

    def test_permission_error(self):
        parl = GrosserRat(db_path=Path('/some/invalid/path'))
        with pytest.raises(PermissionError):
            parl.create_database()


class TestLoadDBFromLocal(TestGrosserRat):
    @classmethod
    def setup_class(cls):
        cls.grosserrat = GrosserRat(db_path='data')

    @classmethod
    def teardown_class(cls):
        del cls.grosserrat

    def test_schema_validity(self, cols_members):
        self.grosserrat.load_db_from_local()
        assert set(cols_members.keys()) == set(self.grosserrat.members)

    def test_schema_validity_wrong_columns(self, cols_members):
        grosserrat_wrong = GrosserRat(db_path='data', db_name='grossrat_wrong_columns')
        grosserrat_wrong.load_db_from_local()
        assert (set(cols_members.keys()) != set(grosserrat_wrong.members))


if __name__ == '__name__':
    pytest.main()
