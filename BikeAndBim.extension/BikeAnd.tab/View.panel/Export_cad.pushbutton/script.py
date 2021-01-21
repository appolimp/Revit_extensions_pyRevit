# coding=utf-8
from rpw import db, DB, UI, uidoc, doc, logger
from pyrevit import forms
from System.Collections.Generic import List
import os.path


class ElemNotFound(Exception):
    pass


VALID_VIEW_TYPE = [DB.ViewType.FloorPlan,
                   DB.ViewType.CeilingPlan,
                   DB.ViewType.Elevation,
                   DB.ViewType.ThreeD,
                   DB.ViewType.DrawingSheet,
                   DB.ViewType.DraftingView,
                   DB.ViewType.EngineeringPlan,
                   DB.ViewType.Section,
                   DB.ViewType.Detail,
                   ]
STANDARD_PREFIX = 'Inter your prefix or ~ for ignore'
DWG_OPTION_NAME = 'RC Layers Standard VBP'


@db.Transaction.ensure('Edit crop view')
def main():
    is_config = not __shiftclick__
    dwg_option_name = get_dwg_option_name(is_config)

    result, folder = export_dwg(dwg_option_name, STANDARD_PREFIX)

    task_dialog('info',
                'Export {} files to <{}>\nExport option is "{}"'.format(len(result), folder, dwg_option_name),
                data=sorted(result))


def get_dwg_option_name(is_config=True):
    if is_config:
        name_option = get_name_option_from_config_or_none()
        if name_option and is_valid_export_option(name_option):
            return name_option

    name_option = get_option_name_from_user()
    set_option_to_config(name_option)

    logger.debug('DWG option: "{}"'.format(name_option))
    return name_option


def get_name_option_from_config_or_none():
    try:
        cfg = get_config()
        if cfg.has_section('Setup_names'):
            section = cfg.get_section('Setup_names')

            file_name = get_file_name_for_config()
            if section.has_option(file_name):
                name_from_config = section.get_option(file_name)

                logger.debug('Get Option name from config: "{}"'.format(name_from_config))
                return name_from_config

    except Exception:
        logger.error('Get error from export config')


def get_file_name_for_config():
    if doc.IsWorkshared:
        path = DB.BasicFileInfo.Extract(doc.PathName).CentralPath
    else:
        path = doc.PathName

    file_name = os.path.split(path)[-1]

    logger.debug('Get file name: {}'.format(file_name))
    return file_name


def set_option_to_config(name_option):
    try:
        cfg = get_config()

        if not cfg.has_section('Setup_names'):
            cfg.add_section('Setup_names')

        section = cfg.get_section('Setup_names')
        file_name = get_file_name_for_config()
        section.set_option(file_name, name_option)

        cfg.save_changes()
        logger.debug('Set Option name "{}" from file: "{}"'.format(name_option, file_name))

    except Exception:
        logger.error('Get error from export config')


def get_config():
    from pyrevit.userconfig import PyRevitConfig
    import os

    this_folder = os.path.dirname(os.path.abspath(__file__))
    init_file = os.path.join(this_folder, 'config.ini')

    cfg = PyRevitConfig(init_file)

    return cfg


def get_option_name_from_user():
    setup_names = DB.BaseExportOptions.GetPredefinedSetupNames(doc)

    res = forms.SelectFromList.show(setup_names,
                                    title='Predefined setup Names for export',
                                    width=300,
                                    height=300,
                                    button_name='Select option for export')

    logger.debug('Get name from user "{}"'.format(res))
    return res


def export_dwg(dwg_option_name, standard_prefix):
    result = []
    views_id = get_selected_views_id()
    dwg_option = get_dwg_option(dwg_option_name)

    path_with_name = get_path(standard_prefix)
    folder, prefix = get_folder_and_prefix_by_path(path_with_name, standard_prefix)

    for view_id in views_id:
        name = prefix + get_name_view_by_id(view_id)
        col = List[DB.ElementId]([view_id])

        doc.Export(folder, name, col, dwg_option)
        delete_pcp_file(folder, name)

        result.append(name)
        logger.debug('View #{}. Export with name "{}"'.format(view_id, name))

    logger.info('Export {} files for folder: <{}>'.format(len(views_id), folder))
    return result, folder


def delete_pcp_file(folder, name):
    path = os.path.join(folder, name + '.pcp')

    if os.path.isfile(path):
        try:
            os.remove(path)
            logger.debug('Delete .pcp file by path <{}>'.format(path))
        except Exception:
            pass


def get_selected_views_id():
    pre_selected = uidoc.Selection.GetElementIds()
    selected_views_id = List[DB.ElementId]()

    for elem_id in pre_selected:
        elem = doc.GetElement(elem_id)
        if elem and isinstance(elem, DB.View) and elem.ViewType in VALID_VIEW_TYPE:
            selected_views_id.Add(elem_id)

    if selected_views_id:
        logger.debug('User select {} views'.format(len(selected_views_id)))
        return selected_views_id

    if doc.ActiveView.ViewType in VALID_VIEW_TYPE:
        logger.debug('Not found any valid selected view. So return ActiveView id')
        return List[DB.ElementId]([doc.ActiveView.Id])

    raise ElemNotFound('Valid selected view and ActiveView not found. ActiveView.ViewType is "{}"'.format(
        doc.ActiveView.ViewType))


def get_name_view_by_id(view_id):
    view = doc.GetElement(view_id)
    if view:
        return make_valid_name(view.Title)

    raise ElemNotFound('View #{}. Not found in document'.format(view_id))


def make_valid_name(name):
    import string

    NON_VALID_CHARACTERS = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']

    valid_name = ''.join(ch if ch not in NON_VALID_CHARACTERS else ' ' for ch in name)

    logger.debug('Name {}. Make valid -> {}'.format(name, valid_name))
    return valid_name


def get_path(prefix):
    window = UI.FileSaveDialog("Файлы AutoCAD 2013 DWG (*.dwg)|*.dwg")
    window.InitialFileName = prefix
    window.Title = 'Choose folder and inter your prefix or ~ for ignore'
    window.Show()

    path = window.GetSelectedModelPath()

    if path:
        string_path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(path)

        logger.debug('Get path from user: <{}>'.format(string_path))
        return string_path

    raise ElemNotFound('Cant get path from user')


def get_folder_and_prefix_by_path(path, standard_prefix):
    folder, name = os.path.split(path)
    prefix, ext = os.path.splitext(name)

    if prefix in [standard_prefix, '~']:
        prefix = ''
    else:
        logger.info('Get prefix: "{}"'.format(prefix))

    logger.info('Get folder <{}>'.format(folder))

    return folder, prefix


def get_dwg_option(option_name):
    if is_valid_export_option(option_name):
        dwg_option = DB.DWGExportOptions.GetPredefinedOptions(doc, option_name)
        dwg_option.FileVersion = DB.ACADVersion.R2013

        logger.debug('Option name is valid: "{}"'.format(option_name))
        return dwg_option

    raise ElemNotFound('Setup name for export not found with name "{}"'.format(option_name))


def is_valid_export_option(option_name):

    setup_names = DB.BaseExportOptions.GetPredefinedSetupNames(doc)
    return option_name in setup_names


def task_dialog(type_mes, msg, data=None):
    """
    For create task dialog with error and message

    :param type_mes: info or error
    :type type_mes: str
    :param msg: Message for window
    :type msg: str
    :param data: Text for expanded content
    :type data: []
    """

    window = UI.TaskDialog('Export CAD')
    window.TitleAutoPrefix = False

    if type_mes == 'info':
        window.MainIcon = UI.TaskDialogIcon.TaskDialogIconInformation
        window.MainInstruction = 'Info'
        window.MainContent = msg
    else:
        window.MainIcon = UI.TaskDialogIcon.TaskDialogIconError
        window.MainInstruction = 'Error'
        window.MainContent = msg

    if data:
        window.ExpandedContent = '\n'.join(data)

    window.CommonButtons = UI.TaskDialogCommonButtons.Ok

    window.Show()


if __name__ == '__main__':
    logger.setLevel(60)

    try:
        main()
    except Exception as err:
        raise
        # task_dialog(type_mes='error', msg='Please, write Nikita', data=err.args)
