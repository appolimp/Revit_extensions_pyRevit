# coding=utf-8
from my_class.base.wrapper import transaction, UnwrapElement, doc, app, Ex, uidoc, TransactionManager, clr, DB, UI
from my_class.base.selection import get_selected_by_cat
from my_class.base.exeption import ScriptError
from Autodesk.Revit.UI.Selection import ISelectionFilter

import logging
from re import findall


OFFSET_DIM_1 = 10 / 304.8
SCALE_WIDTH_TEXT_1_1 = 1.8


class FacesNotOrto(ScriptError):
    pass


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

        logging.debug('Get faces')
        return faces

    def _get_solid(self):
        opt = self.create_option()
        geometry = self.column.get_Geometry(opt)

        for elem in geometry:
            if type(elem) is DB.Solid and elem.Volume:
                logging.debug('Get Solid')
                return elem

        raise ScriptError('Valid solid not found {}')

    def get_parallel_faces_by_dir(self, direct):
        if self._is_parallel(direct, self.vertical):
            logging.debug('Get {} horizontal faces for element as parallel'.format(len(self.horizontal_faces)))
            return self.horizontal_faces

        elif self._is_parallel(direct, self.horizontal):
            logging.debug('Get {} vertical faces for element as parallel'.format(len(self.vertical_faces)))
            return self.vertical_faces

        raise FacesNotOrto('Direction not valid {}'.format(direct))

    def get_perpendicular_faces_by_dir(self, direct):
        if self._is_parallel(direct, self.vertical):
            logging.debug('Get {} vertical faces for element as perpendicular'.format(len(self.horizontal_faces)))
            return self.vertical_faces

        elif self._is_parallel(direct, self.horizontal):
            logging.debug('Get {} horizontal faces for element as perpendicular'.format(len(self.vertical_faces)))
            return self.horizontal_faces

    def create_reference_arr_by_dir(self, direction):
        faces = self.get_parallel_faces_by_dir(direction)

        ref_arr = DB.ReferenceArray()
        for face in faces:
            ref_arr.Append(face.Reference)

        logging.debug('Create ReferenceArray for {} face'.format(ref_arr.Size))
        return ref_arr

    @staticmethod
    def create_option():
        opt = app.Create.NewGeometryOptions()
        opt.ComputeReferences = True

        logging.debug('Option create')
        return opt

    def get_out_line_by_dir_and_offset(self, direction, k_offset=1):

        faces = self.get_perpendicular_faces_by_dir(direction)
        side = self._get_one_face(faces)
        offset = OFFSET_DIM_1 * k_offset * doc.ActiveView.Scale

        center_point = side.Origin + side.FaceNormal * offset
        direction = side.FaceNormal.CrossProduct(DB.XYZ.BasisZ)

        out_line = DB.Line.CreateUnbound(center_point, direction)

        logging.debug('Outline was created with offset = {}'.format(offset))
        return out_line

    @staticmethod
    def _get_one_face(faces):
        for face in faces:
            normal = face.FaceNormal
            if normal.X > 0 or normal.Y < 0:
                logging.debug('Face for outline was found')
                return face

        raise ScriptError('Face for outline not found: ' + str(normal))


class AxlesColumn:
    def __init__(self, column):
        self.column = column

    def get_axles(self):
        axis = self._get_axis()
        return axis

    def _get_axis(self):
        axles_names = self._get_axles_name()
        axles = []
        for axis_name in axles_names:
            axis = self.get_axis_by_name(axis_name)
            logging.debug('Axis with name {} selected'.format(axis.Name))
            axles.append(axis)

        return axles

    def _get_axles_name(self):
        axis_param = self.column.get_Parameter(DB.BuiltInParameter.COLUMN_LOCATION_MARK)
        logging.debug('Get axis value: ' + axis_param.AsString())

        axles_names = self._find_axles_name(axis_param.AsString())
        return axles_names

    @staticmethod
    def _find_axles_name(value):
        REGEX = r"(.+?)(?:\([\d-]+?\))??-([\w/]+)(?:\([\d-]+?\))?"
        result = findall(REGEX, value)[0]

        logging.debug('Get axis name: "{}"'.format(result))
        return result

    def get_axis_by_name(self, name):
        multi_grids = self._get_elem_by_name_and_cat(name, DB.BuiltInCategory.OST_GridChains)
        if multi_grids:
            grid = self.find_nearest_grid(multi_grids)

            return grid

        logging.debug('Multi-grids with name {} not found'.format(name))
        grid = self._get_elem_by_name_and_cat(name, DB.BuiltInCategory.OST_Grids)
        return grid

    @staticmethod
    def _get_elem_by_name_and_cat(name, category):
        collector = DB.FilteredElementCollector(doc)
        elems = collector.OfCategory(category).WhereElementIsNotElementType()
        for elem in elems:
            if elem.Name == name:
                logging.debug('Elements with name {} was found'.format(name))
                return elem

    def find_nearest_grid(self, multi_grids):
        grids = self.get_grids_by_multi(multi_grids)
        origin = self.column.Location.Point

        nearest_grid = self._find_nearest_grid(grids, origin)

        logging.debug('Nearest grid for {} was found'.format(multi_grids.Name))
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

        logging.debug('Multi-grids was divided by {}'.format(len(grids)))
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

        logging.debug('Text position was moved by {}'.format(vector))

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

        logging.debug('Calc shift: {}'.format(shift))
        return shift

    @property
    def text_ratio(self):
        if self._text_ratio is None:
            scale = doc.ActiveView.Scale
            width = self._get_width_by_dim_type(self.dimension.DimensionType)

            self._text_ratio = SCALE_WIDTH_TEXT_1_1 * scale * width
            logging.debug('Get text ratio: ' + str(self._text_ratio))

        return self._text_ratio

    @staticmethod
    def _get_width_by_dim_type(dim_type):
        parameter = dim_type.get_Parameter(DB.BuiltInParameter.TEXT_WIDTH_SCALE)
        width = parameter.AsDouble()
        return width


@transaction
def main():
    K_OFFSET = IN[0]
    K_SPACE = IN[1]
    K_SHIFT_SPACE = IN[2]

    columns = get_columns()
    for column in columns:
        dims = create_dim_for_column(column, K_OFFSET, K_SPACE, K_SHIFT_SPACE)

    logging.info('Create dimension for {} columns '.format(len(columns)))


def create_dim_for_column_and_grid(column, grid, k_offset=4):

    direction = grid.Curve.Direction
    edge = ColumnEdge(column)

    ref_arr = edge.create_reference_arr_by_dir(direction)
    ref_arr.Append(DB.Reference(grid))

    out_line = edge.get_out_line_by_dir_and_offset(direction, k_offset)

    dim = doc.Create.NewDimension(doc.ActiveView, out_line, ref_arr)

    logging.debug('Create dimension: ' + dim.Name)
    return dim


def create_dim_for_column(column, k_offset=4, k_space=1, k_shift_space=0.8):

    grids = AxlesColumn(column).get_axles()

    dims = []
    for grid in grids:
        try:
            dim = create_dim_for_column_and_grid(column, grid, k_offset)
        except FacesNotOrto:
            logging.error('Problem with face for {} in {}-{} '.format(
                grid.Name, grids[0].Name, grids[1].Name))
            continue

        dims.append(dim)

        # TODO add 1 segment
        if dim.Segments.Size == 2:
            text_position = Dim2TextPosition(dim, k_space, k_shift_space)
            text_position.update()
        else:
            logging.error('Dim for column at axles {}-{} have 1 segments for {}'.format(
                grids[0].Name, grids[1].Name, grid.Name))

    logging.debug('Create {} dimension for column'.format(len(dims)))

    return dims


def get_columns():
    selected_column = get_selected_by_cat(DB.BuiltInCategory.OST_StructuralColumns, as_list=True)
    if selected_column:
        return selected_column

    columns = user_selection_columns()
    return columns


def user_selection_columns():
    columns = uidoc.Selection.PickElementsByRectangle(ColumnFilter(), 'select columns')
    logging.info('User select {}'.format(len(columns)))
    return columns


if __name__ == '__main__':
    logging.basicConfig(
        filename=None, level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    try:
        main()
    except ScriptError as e:
        logging.error(e)
    except Exception as err:
        logging.exception('Critical error')
