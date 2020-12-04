from wrapper import doc, DB, UI, clr


from System.Collections.Generic import List

from Autodesk.Revit.Exceptions import ApplicationException, ArgumentException

OPTIONS = DB.Options()
# OPTIONS.IncludeNonVisibleObjects = True
OPTIONS.ComputeReferences = True


def get_solids(element, options=OPTIONS):
    geo = element.get_Geometry(options)
    solids = []
    for g in geo:
        # GeometryInstance
        if type(g) == DB.GeometryInstance:
            transform = g.Transform
            symbol_geo = g.SymbolGeometry
            symbol_mat = symbol_geo.MaterialElement
            for sub_g in symbol_geo.GetTransformed(g.Transform):
                if type(sub_g) == DB.Solid and sub_g.Volume > 0:
                    solids.append(sub_g)
        if type(g) == DB.Solid and g.Volume > 0:
            solids.append(g)
    return solids


def collect_by_bbox(element, offset=0.3, collector=None):
    bbox = element.get_BoundingBox(None)
    outline = DB.Outline(
        DB.XYZ(bbox.Min.X - offset, bbox.Min.Y - offset, bbox.Min.Z - offset),
        DB.XYZ(bbox.Max.X + offset, bbox.Max.Y + offset, bbox.Max.Z + offset))
    bbox_filter = DB.BoundingBoxIntersectsFilter(outline)
    ids_to_exclude = List[DB.ElementId]([element.Id])
    if not collector:
        collector = DB.FilteredElementCollector(doc).Excluding(ids_to_exclude).WherePasses(bbox_filter)
    else:
        collector.Excluding(ids_to_exclude).WherePasses(bbox_filter)
    return collector


def join_geometry(a, b):
    joined = DB.JoinGeometryUtils.AreElementsJoined(doc, a, b)
    if not joined:
        try:
            return DB.JoinGeometryUtils.JoinGeometry(doc, a, b)
        except ArgumentException:
            pass


def unjoin_geometry(a, b):
    joined = DB.JoinGeometryUtils.AreElementsJoined(doc, a, b)
    if joined:
        return DB.JoinGeometryUtils.UnjoinGeometry(doc, a, b)


def switch_geometry(a, b):
    joined = DB.JoinGeometryUtils.AreElementsJoined(doc, a, b)
    if joined:
        return DB.JoinGeometryUtils.SwitchJoinOrder(doc, a, b)


def join_neighbors_by_bbox(element, collector=None):
        collector = collect_by_bbox(element, collector=collector)
        if collector:
            for other in collector:
                join_geometry(element, other)


def unjoin_neighbors_by_bbox(element):
    collector = collect_by_bbox(element)
    if collector:
        for other in collector:
            unjoin_geometry(element, other)


def switch_neighbors_by_bbox(element):
    collector = collect_by_bbox(element)
    if collector:
        for other in collector:
            switch_geometry(element, other)


def join_all(elements, unjoin=False):
    pairs = set()
    for i, ea in enumerate(elements):
        for j, eb in enumerate(elements):
            if i != j:
                pair = i, j
                reversed_pair = j, i
                if pair not in pairs and reversed_pair not in pairs:
                    if unjoin:
                        unjoin_geometry(ea, eb)
                    else:
                        join_geometry(ea, eb)
                pairs.add(pair)


def cut_all_instances_by_geometry_intersect(elements, uncut=False):
    for element in elements:
        el_col = collect_by_intersect(element)
        if not el_col:
            return
        for other in el_col:
            if uncut:
                uncut_instance_geometry(other, element)
            else:
                cut_instance_geometry(other, element)


def collect_by_intersect(element):
    element_solids = get_solids(element)
    if not element_solids:
        return
    element_solid = get_solids(element)[0]
    collector = collect_by_bbox(element)
    collector.WherePasses(DB.ElementIntersectsSolidFilter(element_solid))
    return collector


def cut_instance_geometry(a, b):
    # DB.SolidSolidCutUtils.AddCutBetweenSolids(doc, a, b)
    DB.InstanceVoidCutUtils.AddInstanceVoidCut(doc, a, b)


def uncut_instance_geometry(a, b):
    DB.InstanceVoidCutUtils.RemoveInstanceVoidCut(doc, a, b)



def flip_wall(wall):
    """Set Location Line to Wall Center, Flip and set Location Line back"""
    bpn_loc_line = DB.BuiltInParameter.WALL_KEY_REF_PARAM
    bp_loc_line = wall.get_Parameter(bpn_loc_line)
    bpv_loc_line = bp_loc_line.AsInteger()
    bp_loc_line.Set(0)
    wall.Flip()
    if bpv_loc_line == 2:
        bp_loc_line.Set(3)
    elif bpv_loc_line == 3:
        bp_loc_line.Set(2)
    elif bpv_loc_line == 4:
        bp_loc_line.Set(5)
    elif bpv_loc_line == 5:
        bp_loc_line.Set(4)
    else:
        bp_loc_line.Set(bpv_loc_line)


def miter_join_framings(framings):
    """Set mitter joins for selected framings"""

    for framing in framings:
        # select first start/end joins
        # TODO: add selecting join by angle or similar way
        joins = get_element_joins(framing)
        start_join = joins[0][0] if joins[0] else None
        end_join = joins[1][0] if joins[1] else None

        if not any([start_join, end_join]):
            continue

        # if join exist and its type does not mitter
        extention = framing.ExtensionUtility
        if start_join:
            start_has_mitter = extention.get_HasMiter(0)
            if not start_has_mitter:
                # set start join mitter
                extention.set_Extended(0, True)
        if end_join:
            end_has_mitter = extention.get_HasMiter(1)
            if not end_has_mitter:
                # set end join mitter
                extention.set_Extended(1, True)


def miter_join_walls(elements):
    """Set mitter joins for selected walls"""

    for element in elements:
        # select first start/end joins
        # TODO: add selecting walls join by angle or similar way

        location = element.Location

        joins = get_element_joins(element)
        start_join = joins[0][0] if joins[0] else None
        end_join = joins[1][0] if joins[1] else None

        if not any([start_join, end_join]):
            continue
        if start_join:
            start_join_type = location.get_JoinType(0)
            if start_join_type != DB.JoinType.Miter:
                # set start join mitter
                location.set_JoinType(0, DB.JoinType.Miter)
        if end_join:
            end_join_type = location.get_JoinType(1)
            if end_join_type != DB.JoinType.Miter:
                # set start join mitter
                location.set_JoinType(1, DB.JoinType.Miter)


def get_element_joins(element):
    """Return two list of ElementsAtJoins (start, end)"""
    e_id = element.Id
    location = element.Location
    start_joins = [e for e in location.get_ElementsAtJoin(0) if e.Id != e_id]
    end_joins = [e for e in location.get_ElementsAtJoin(1) if e.Id != e_id]

    return start_joins, end_joins
