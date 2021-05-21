# coding=utf-8
""" Создание размеров привязки колонн к осям

    Packages:

    Author:
        - Nikita Glebov
"""

# ################# Проблемы ################################################
# FIXME Не находит оси через "-" (10-5). Создавать такие оси - была большая ошибка(

# ################# Стандартный импорт ######################################
from rpw import revit, db, ui, doc, uidoc, logger, DB, UI


app = revit.app
from System.Collections.Generic import List
from Autodesk.Revit.UI.Selection import ISelectionFilter


# ################# Импорт python библиотек #################################
import sys

sys.path.append(r"C:\Program Files (x86)\IronPython 2.7\Lib")
import functools
from re import findall


# ################# Константы ###############################################
OFFSET_DIM_1 = 10 / 304.8
SCALE_WIDTH_TEXT_1_1 = 1.8

K_OFFSET = 1  # коэффициент отступа размерной линии
K_SPACE = 1  # коэффициент ширины, определяет нужно ли смещение или нет
K_SHIFT_SPACE = 0.8  # коэффициент пространства смещения

URL_TO_DOCUMENTATION = r"https://docs.google.com/document/d/16s43SdnfCyw-gwgtgorSO4wkfVKOD6HLL8TmPYUnhyw/edit?usp=sharing"  # Ссылка на документацию


# ################# Базовые функции #########################################
def transaction(func):
    """
    Выполнение обращений к Revit внутри транзакций

    Выполнено в виде декоратора

    :param func: декорируемую функция
    :return: функция с включением и выключением транзакции
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        trans = DB.Transaction(doc, '11')
        trans.Start()

        res = func(*args, **kwargs)

        trans.Commit()
        return res

    return wrapped


def task_dialog(type_mes, msg, data=None):
    """
    For create task dialog with error and message

    :param type_mes: info or error
    :type type_mes: str
    :param msg: Message for window
    :type msg: str
    :param data: Text for expanded content
    :type data: list
    """

    window = UI.TaskDialog('Заполнение MCP параметров')
    window.TitleAutoPrefix = False

    if type_mes == 'info':
        window.MainIcon = UI.TaskDialogIcon.TaskDialogIconInformation
        window.MainInstruction = 'Info'
        window.MainContent = msg
    else:
        window.MainIcon = UI.TaskDialogIcon.TaskDialogIconWarning
        window.MainInstruction = 'Error'
        window.MainContent = msg
        window.FooterText = ("<a href=\"{}\"> ".format(URL_TO_DOCUMENTATION) +
                             "Нажмите сюда, чтобы открыть документацию</a>")
        logger.error(msg)

    if data:
        window.ExpandedContent = data if isinstance(data, str) else '\n'.join(data)

    window.CommonButtons = UI.TaskDialogCommonButtons.Ok

    window.Show()


class ScriptError(Exception):
    """Ошибки во время выполнения скрипта"""

    def __init__(self, mes):
        super(ScriptError, self).__init__(mes)
        # logger.error(mes)


class ElemNotFound(ScriptError):
    """Ошибка когда не найден элемент"""
    pass


class FacesNotOrto(ScriptError):
    pass


def get_selected_by_cat(categories):
    """

    :type categories: list[DB.BuiltInCategory]
    :rtype: list[DB.Element]
    """

    selections_id = uidoc.Selection.GetElementIds()
    if selections_id:
        categories_list = List[DB.BuiltInCategory](categories)
        filter_cat = DB.ElementMulticategoryFilter(categories_list)

        collector = DB.FilteredElementCollector(doc, selections_id).WherePasses(filter_cat).ToElements()

        logger.debug('Get selected by category {}'.format(len(collector)))
        return collector


class ColumnFilter(ISelectionFilter):
    def AllowElement(self, elem):
        column_id = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_StructuralColumns).Id
        if elem.Category.Id == column_id:
            return True
        return False


class ColumnEdge:
    def __init__(self, column):
        self.column = column
        self.vertical = column.FacingOrientation
        self.horizontal = column.HandOrientation

        self._fill_faces()

    def _fill_faces(self):
        faces = self._get_faces()
        vertical_faces = []
        horizontal_faces = []

        for face in faces:
            normal = face.FaceNormal

            if self._is_parallel(normal, self.vertical):
                vertical_faces.append(face)

            elif self._is_parallel(normal, self.horizontal):
                horizontal_faces.append(face)

            elif abs(round(face.FaceNormal.Z, 3)) == 1:
                pass
            else:
                raise FacesNotOrto(str(face.FaceNormal))

        self.vertical_faces = vertical_faces[:2]
        self.horizontal_faces = horizontal_faces[:2]

    @staticmethod
    def _is_parallel(first, second):
        prod = first.CrossProduct(second)
        res = prod.IsAlmostEqualTo(DB.XYZ.Zero, 0.001)
        return res

    def _get_faces(self):
        solid = self._get_solid()
        faces = solid.Faces

        logger.debug('Get faces')
        return faces

    def _get_solid(self):
        opt = self.create_option()
        geometry = self.column.get_Geometry(opt)

        for elem in geometry:
            if type(elem) is DB.Solid and elem.Volume:
                logger.debug('Get Solid')
                return elem

        raise ScriptError('Valid solid not found {}')

    def get_parallel_faces_by_dir(self, direct):
        if self._is_parallel(direct, self.vertical):
            logger.debug('Get {} horizontal faces for element as parallel'.format(len(self.horizontal_faces)))
            return self.horizontal_faces

        elif self._is_parallel(direct, self.horizontal):
            logger.debug('Get {} vertical faces for element as parallel'.format(len(self.vertical_faces)))
            return self.vertical_faces

        raise FacesNotOrto('Direction not valid {}'.format(direct))

    def get_perpendicular_faces_by_dir(self, direct):
        if self._is_parallel(direct, self.vertical):
            logger.debug('Get {} vertical faces for element as perpendicular'.format(len(self.horizontal_faces)))
            return self.vertical_faces

        elif self._is_parallel(direct, self.horizontal):
            logger.debug('Get {} horizontal faces for element as perpendicular'.format(len(self.vertical_faces)))
            return self.horizontal_faces

    def create_reference_arr_by_dir(self, direction):
        faces = self.get_parallel_faces_by_dir(direction)

        ref_arr = DB.ReferenceArray()
        for face in faces:
            ref_arr.Append(face.Reference)

        logger.debug('Create ReferenceArray for {} face'.format(ref_arr.Size))
        return ref_arr

    @staticmethod
    def create_option():
        opt = app.Create.NewGeometryOptions()
        opt.ComputeReferences = True

        logger.debug('Option create')
        return opt

    def get_out_line_by_dir_and_offset(self, direction, k_offset=1):

        faces = self.get_perpendicular_faces_by_dir(direction)
        side = self._get_one_face(faces)
        offset = OFFSET_DIM_1 * k_offset * doc.ActiveView.Scale

        center_point = side.Origin + side.FaceNormal * offset
        direction = side.FaceNormal.CrossProduct(DB.XYZ.BasisZ)

        out_line = DB.Line.CreateUnbound(center_point, direction)

        logger.debug('Outline was created with offset = {}'.format(offset))
        return out_line

    @staticmethod
    def _get_one_face(faces):
        for face in faces:
            normal = face.FaceNormal
            if normal.X > 0 or normal.Y < 0:
                logger.debug('Face for outline was found')
                return face

        raise ScriptError('Face for outline not found')


class AxlesColumn:
    def __init__(self, column):
        self.column = column

    def get_axles(self):
        axis = self._get_axis()
        logger.debug('#{} Column. Get {} axles'.format(self.column.Id, len(axis)))
        return axis

    def _get_axis(self):
        axles_names = self._get_axles_name()
        axles = []
        for axis_name in axles_names:
            try:
                axis = self.get_axis_by_name(axis_name)
                logger.debug('Axis with name {} selected'.format(axis.Name))
                axles.append(axis)
            except ElemNotFound:
                logger.error('Can not found axles with name: "{}"'.format(axis_name))

        return axles

    def _get_axles_name(self):
        axis_param = self.column.get_Parameter(DB.BuiltInParameter.COLUMN_LOCATION_MARK)
        logger.debug('Get axis value: ' + axis_param.AsString())

        axles_names = self._find_axles_name(axis_param.AsString())
        return axles_names

    @staticmethod
    def _find_axles_name(value):
        REGEX = r"(.+?)(?:\([\d-]+?\))??-([\w/]+)(?:\([\d-]+?\))?"
        result = findall(REGEX, value)[0]

        logger.debug('Get axis name: "{}"'.format(result))
        return result

    def get_axis_by_name(self, name):
        try:
            multi_grids = self._get_elem_by_name_and_cat(name, DB.BuiltInCategory.OST_GridChains)
            grid = self.find_nearest_grid(multi_grids)
            return grid

        except ElemNotFound:
            logger.debug('Multi-grids with name {} not found'.format(name))
            grid = self._get_elem_by_name_and_cat(name, DB.BuiltInCategory.OST_Grids)
            return grid

    @staticmethod
    def _get_elem_by_name_and_cat(name, category):
        collector = DB.FilteredElementCollector(doc)
        elems = collector.OfCategory(category).WhereElementIsNotElementType()
        for elem in elems:
            if elem.Name == name:
                logger.debug('Elements with name {} was found'.format(name))
                return elem

        raise ElemNotFound('Not found. Element with name "{}" and category "{}"'.format(name, category))

    def find_nearest_grid(self, multi_grids):
        grids = self.get_grids_by_multi(multi_grids)
        origin = self.column.Location.Point

        nearest_grid = self._find_nearest_grid(grids, origin)

        logger.debug('Nearest grid for {} was found'.format(multi_grids.Name))
        return nearest_grid

    @staticmethod
    def _find_nearest_grid(grids, point):
        def compare(grid):
            line = grid.Curve
            distance = line.Distance(point)
            return distance

        nearest = min(grids, key=compare)

        return nearest

    @staticmethod
    def get_grids_by_multi(multi_grids):
        grids = []
        for grid_id in multi_grids.GetGridIds():
            grid = doc.GetElement(grid_id)
            grids.append(grid)

        logger.debug('Multi-grids was divided by {}'.format(len(grids)))
        return grids


class Dim2TextPosition:
    def __init__(self, dimension, k_space=1, k_shift_space=0.8):
        self.dimension = dimension
        self.left, self.right = self.find_side_dims(dimension)
        self.direction = (self.left.Origin - self.right.Origin).Normalize()
        self.k_space = k_space
        self.k_shift_space = k_shift_space
        self._text_ratio = None

    @staticmethod
    def find_side_dims(dimension):
        first, second = dimension.Segments
        direction = second.Origin - first.Origin
        if direction.X > 0 or direction.Y < 0:
            return first, second
        return second, first

    def update(self):
        left_shift = self.calc_shift(self.left)
        right_shift = self.calc_shift(self.right)

        if left_shift:
            self.update_text_position_by_vector(self.left, self.direction * left_shift)
        if right_shift:
            self.update_text_position_by_vector(self.right, -self.direction * right_shift)

    @staticmethod
    def update_text_position_by_vector(dim, vector):
        pos = dim.TextPosition
        new_pos = DB.Transform.CreateTranslation(vector).OfPoint(pos)
        dim.TextPosition = new_pos

        logger.debug('Text position was moved by {}'.format(vector))

    def calc_shift(self, segment):
        value = segment.ValueString
        width = len(value) * self.text_ratio
        space = self.k_space * self.text_ratio

        if float(value.replace(',', '.')) > width + space:
            return 0
        return self._calc_shift(segment)

    def _calc_shift(self, segment):
        width_dim = segment.Value
        space = (self.k_shift_space * self.text_ratio) / 304.8
        width_text = len(segment.ValueString) * self.text_ratio / 304.8

        shift = width_dim / 2 + space + width_text / 2

        logger.debug('Calc shift: {}'.format(shift))
        return shift

    @property
    def text_ratio(self):
        if self._text_ratio is None:
            scale = doc.ActiveView.Scale
            width = self._get_width_by_dim_type(self.dimension.DimensionType)

            self._text_ratio = SCALE_WIDTH_TEXT_1_1 * scale * width
            logger.debug('Get text ratio: ' + str(self._text_ratio))

        return self._text_ratio

    @staticmethod
    def _get_width_by_dim_type(dim_type):
        parameter = dim_type.get_Parameter(DB.BuiltInParameter.TEXT_WIDTH_SCALE)
        width = parameter.AsDouble()
        return width


@transaction
def main():
    columns = get_columns()
    for column in columns:
        try:  # TODO Переписать нормально. Без try или не в этом месте
            create_dim_for_column(column, doc.ActiveView, K_OFFSET, K_SPACE, K_SHIFT_SPACE)
        except Exception as err:
            logger.error(err)

    logger.info('Create dimension for {} columns '.format(len(columns)))


def create_dim_for_column_and_grid(column, grid, view, k_offset=4):
    direction = grid.Curve.Direction
    edge = ColumnEdge(column)

    ref_arr = edge.create_reference_arr_by_dir(direction)
    ref_arr.Append(DB.Reference(grid))

    out_line = edge.get_out_line_by_dir_and_offset(direction, k_offset)

    dim = doc.Create.NewDimension(view, out_line, ref_arr)

    logger.debug('Create dimension: ' + dim.Name)
    return dim


def create_dim_for_column(column, view, k_offset=4, k_space=1, k_shift_space=0.8):
    try:
        grids = AxlesColumn(column).get_axles()

        dims = []
        for grid in grids[:1]:
            try:
                dim = create_dim_for_column_and_grid(column, grid, view, k_offset)
            except FacesNotOrto:
                logger.error('Problem with face for {} in {}-{} '.format(
                    grid.Name, grids[0].Name, grids[1].Name))
                continue

            dims.append(dim)

            # TODO add 1 segment
            if dim.Segments.Size == 2:
                text_position = Dim2TextPosition(dim, k_space, k_shift_space)
                text_position.update()
            else:
                logger.error('Dim for column at axles {}-{} have 1 segments for {}'.format(
                    grids[0].Name, grids[1].Name, grid.Name))

        logger.debug('#{} Column. Create {} dimension'.format(column.Id, len(dims)))
    except Exception:
        raise ScriptError('Can not create dim')

    return dims[0]


def get_columns():
    selected_column = get_selected_by_cat([DB.BuiltInCategory.OST_StructuralColumns])
    if selected_column:
        return selected_column

    columns = user_selection_columns()
    return columns


def user_selection_columns():
    columns = uidoc.Selection.PickElementsByRectangle(ColumnFilter(), 'select columns')
    logger.info('User select {}'.format(len(columns)))
    return columns


if __name__ == '__main__':
    logger.basicConfig(
        filename=None, level=logger.DEBUG,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    try:
        main()
    except ScriptError as e:
        task_dialog('error', e.args[0])
        logger.exception(e)

    except Exception as err:
        task_dialog('error', err.args[0])
        logger.exception('Critical error')
