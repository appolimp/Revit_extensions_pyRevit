from base.wrapper import DB, app
from base.exeption import ElemNotFound

import logging


class GeometryInRevit(object):
    """
    Work with geometry of Revit Element:

    - Get solid of instance
    """

    @classmethod
    def get_geom_by_elem(cls, element):
        """
        Get instance solid for given element

        :param element: DB.Element
        :return: DB.Solid
        """

        option = cls.create_option()
        geometry = element.get_Geometry(option)

        return cls._get_solid_by_geom(geometry)

    @classmethod
    def _get_solid_by_geom(cls, geometry):
        for elem in geometry:
            if type(elem) is DB.Solid and elem.Volume:
                logging.debug('Get Solid')
                return elem

        logging.debug('Solid not found')

        for elem in geometry:
            if type(elem) is DB.GeometryInstance:
                logging.debug('Get GeometryInstance')
                symbol_geom = elem.GetSymbolGeometry()

                return cls._get_solid_by_geom(symbol_geom)

        raise ElemNotFound('Valid solid or GeometryInstance not found {}')

    @staticmethod
    def create_option():
        """
        Create user preferences for parsing of geometry

        In this case View == None, get References == True

        :return: DB.Options
        """

        opt = app.Create.NewGeometryOptions()
        opt.ComputeReferences = True

        logging.debug('Option create')
        return opt

    @classmethod
    def get_up_face(cls, element, vector):
        """
        Get upper face of element

        :return: Upper face of element, DB.Face
        """

        solid = cls.get_geom_by_elem(element)

        faces = []
        for face in solid.Faces:
            if face.FaceNormal.IsAlmostEqualTo(vector, 0.1):
                faces.append(face)
        if not faces:
            raise ElemNotFound('Face up not found')
        elif len(faces) == 1:
            my_face = faces[0]
        else:
            my_face = max(faces, key=lambda x: x.FaceNormal.Z * vector.Z)

        logging.debug('Get face by vector: {}, face origin == {}'.format(vector, my_face.Origin))
        return my_face
