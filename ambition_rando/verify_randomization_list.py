import csv
import os

from django.apps import apps as django_apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError, ProgrammingError

from .utils import get_drug_assignment


def verify_randomization_list():
    message = None
    app_config = django_apps.get_app_config('ambition_rando')
    model_cls = django_apps.get_model('ambition_rando.randomizationlist')
    try:
        count = model_cls.objects.all().count()
    except (ProgrammingError, OperationalError) as e:
        message = str(e)
    else:
        if count == 0:
            message = (
                'Randomization list has not been loaded. '
                'Run the \'import_randomization_list\' management command '
                'to load before using the system. '
                'Resolve this issue before using the system.')

        else:
            if not os.path.exists(app_config.randomization_list_path):
                message = (
                    f'Randomization list file does not exist but SIDs have been loaded. '
                    f'Expected file {app_config.randomization_list_path}. '
                    f'Resolve this issue before using the system.')
            else:
                with open(app_config.randomization_list_path, 'r') as f:
                    fieldnames = ['sid', 'drug_assignment', 'site_name']
                    reader = csv.DictReader(
                        f, fieldnames=fieldnames)
                    for index, row in enumerate(reader):
                        row = {k: v.strip()
                               for k, v in row.items() if k in fieldnames}
                        if index == 0:
                            continue
                        try:
                            obj = model_cls.objects.get(sid=row['sid'])
                        except ObjectDoesNotExist:
                            obj = model_cls.objects.all()[index]
                            message = (
                                f'Randomization list is invalid. List has invalid SIDs. '
                                f'File data does not match model data. See file '
                                f'{app_config.randomization_list_path}. '
                                f'Resolve this issue before using the system. '
                                f'Problem started on line {index + 1}. '
                                f'Got {row["sid"]} != {obj.sid}.')
                            break
                        else:
                            drug_assignment = get_drug_assignment(row)
                            if (obj.drug_assignment != drug_assignment
                                    or obj.site_name != row['site_name']):
                                message = (
                                    f'Randomization list is invalid. File data '
                                    f'does not match model data. See file '
                                    f'{app_config.randomization_list_path}. '
                                    f'Resolve this issue before using the system. '
                                    f'Got {drug_assignment} != \'{obj.drug_assignment}\'.')
                                break
                if not message:
                    with open(app_config.randomization_list_path, 'r') as f:
                        reader = csv.DictReader(
                            f, fieldnames=['sid', 'drug_assignment', 'site_name'])
                        lines = sum(1 for row in reader)
                    if count != lines - 1:
                        message = (
                            f'Randomization list count is off. Expected {count}. '
                            f'Got {lines - 1}. See file '
                            f'{app_config.randomization_list_path}. '
                            f'Resolve this issue before using the system.')
    return message
