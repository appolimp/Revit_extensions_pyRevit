from base.wrapper import doc, DB, Transaction
import logging


@Transaction.ensure('Create sheet')
def create_sheet(title_block_id=DB.ElementId(-1)):
    """
    Create new sheet on current document by TitleBlock

    :param title_block_id: TitleBlock id
    :type title_block_id: DB.ElementId
    :return: New Sheet
    :rtype: DB.ViewSheet
    """

    sheet = DB.ViewSheet.Create(doc, title_block_id)

    logging.debug('Sheet was created: "{}"'.format(sheet.Name))
    return sheet


def add_view_to_sheet(view, sheet, position=DB.XYZ(0, 0, 0)):
    view_port = DB.Viewport.Create(doc, sheet.Id, view.Id, position)

    logging.debug('Viewport was created: "{}"'.format(view_port.Name))
    return view_port


def create_sheet_by_views(views, name):
    sheet = create_sheet()
    set_name_for_sheet(sheet, name)

    viewports = []

    with Transaction('Add view port'):
        for view in views:
            viewport = add_view_to_sheet(view, sheet)
            viewports.append(viewport)

    _correct_positions(viewports)

    logging.info('Sheet "{}" with {} viewports was created'.format(name, len(viewports)))
    return sheet


@Transaction.ensure('Correct position on viewports')
def _correct_positions(viewports, start=DB.XYZ(0, 0, 0)):
    last_right = start
    for viewport in viewports:
        _correct_position_right(viewport, last_right, shift=0.1)
        last_right = viewport.GetBoxOutline().MaximumPoint


def _correct_position_right(viewport, last_right_up, shift=0.1):
    box = viewport.GetBoxOutline()
    center = viewport.GetBoxCenter()
    up, down = box.MaximumPoint, box.MinimumPoint

    shift_center = center + DB.XYZ(shift, 0, 0)
    new_center = shift_center - DB.XYZ(down.X - last_right_up.X,
                                       up.Y - last_right_up.Y, 0)
    viewport.SetBoxCenter(new_center)
    logging.debug('Set new position: {:.3f}, {:.3f}'.format(new_center.X, new_center.Y))
    return


@Transaction.ensure('Set sheet name')
def set_name_for_sheet(sheet, name):
    sheet.Name = name

    logging.debug('Set name for sheet: "{}"'.format(name))

