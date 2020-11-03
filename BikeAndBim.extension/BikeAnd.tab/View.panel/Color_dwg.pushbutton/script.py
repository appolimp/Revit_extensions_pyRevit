# coding=utf-8

from rpw import db, ui, doc, logger, DB
import System


@db.Transaction.ensure('Color dwg')
def main():
    logger.debug('Start')
    dwg_elems = get_dwgs()
    graphic = create_graphic(color_hex='##0080c0')
    for imp_dwg in dwg_elems:
        set_visible(imp_dwg, up=True)
        set_graphic(imp_dwg, graphic)


def get_dwgs():
    selection_elems = ui.Selection()
    for elem in selection_elems:
        if type(elem.unwrap()) is DB.ImportInstance:
            logger.debug('Get selected dwg: {}'.format(elem.get_category().name))
            yield elem


def set_visible(elem, up=True):
    param = elem.parameters.builtins['IMPORT_BACKGROUND']
    param.value = not up
    logger.debug('Set visible on {}'.format('up' if up else 'down'))


def set_graphic(elem, graphic):
    doc.ActiveView.SetElementOverrides(elem.Id, graphic)
    logger.debug('Graphic was overrides')


def create_graphic(color_hex):
    color = hex_string_to_color(color_hex)
    graphic = DB.OverrideGraphicSettings()
    graphic.SetProjectionLineColor(color)

    logger.debug('Graphic was created')
    return graphic


def hex_string_to_color(hex_str):
    """Получения цвета из HEX"""
    hex_str = hex_str.lstrip('##')
    r, g, b = (int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    color = DB.Color(System.Byte(r), System.Byte(g), System.Byte(b))

    logger.debug('Color was created')
    return color


if __name__ == '__main__':
    main()
