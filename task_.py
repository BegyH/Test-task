import traceback
import math
import coordinates_dir

import NXOpen
import NXOpen_Features
import NXOpen_UF

# следующие импорты


class task:
    # static class members
    theSession = None
    theUI = None
    # ------------------------------------------------------------------------------
    # Bit Option for Property: EntityType
    # ------------------------------------------------------------------------------
    EntityType_AllowFaces = 1 << 4
    EntityType_AllowDatums = 1 << 5
    EntityType_AllowBodies = 1 << 6
    # ------------------------------------------------------------------------------
    # Bit Option for Property: FaceRules
    # ------------------------------------------------------------------------------
    FaceRules_SingleFace = 1 << 0
    FaceRules_RegionFaces = 1 << 1
    FaceRules_TangentFaces = 1 << 2
    FaceRules_TangentRegionFaces = 1 << 3
    FaceRules_BodyFaces = 1 << 4
    FaceRules_FeatureFaces = 1 << 5
    FaceRules_AdjacentFaces = 1 << 6
    FaceRules_ConnectedBlendFaces = 1 << 7
    FaceRules_AllBlendFaces = 1 << 8
    FaceRules_RibFaces = 1 << 9
    FaceRules_SlotFaces = 1 << 10
    FaceRules_BossandPocketFaces = 1 << 11
    FaceRules_MergedRibFaces = 1 << 12
    FaceRules_RegionBoundaryFaces = 1 << 13
    FaceRules_FaceandAdjacentFaces = 1 << 14
    FaceRules_HoleFaces = 1 << 15

    def __init__(self):
        try:
            self.theSession = NXOpen.Session.GetSession()
            self.theUI = NXOpen.UI.GetUI()
            self.theDlxFileName = "task.dlx"
            self.theDialog = self.theUI.CreateDialog(self.theDlxFileName)
            self.theDialog.AddApplyHandler(self.apply_cb)
            self.theDialog.AddOkHandler(self.ok_cb)
            self.theDialog.AddUpdateHandler(self.update_cb)
            self.theDialog.AddInitializeHandler(self.initialize_cb)
            self.theDialog.AddDialogShownHandler(self.dialogShown_cb)
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            raise ex

    def Show(self):
        try:
            self.theDialog.Show()
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            self.theUI.NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))

    def Dispose(self):
        if self.theDialog != None:
            self.theDialog.Dispose()
            self.theDialog = None

    def initialize_cb(self):
        try:
            self.group0 = self.theDialog.TopBlock.FindBlock("group0")
            self.Amount = self.theDialog.TopBlock.FindBlock("Amount")
            self.Size = self.theDialog.TopBlock.FindBlock("Size")
            self.face_select0 = self.theDialog.TopBlock.FindBlock("face_select0")
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            self.theUI.NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))

    def draw_block(self, points, normal, center_point):
        center = NXOpen.Point3d(center_point[0], center_point[1], center_point[2])
        theSession = NXOpen.Session.GetSession()
        workPart = theSession.Parts.Work
        displayPart = theSession.Parts.Display
        pointsNX = [0, 0, 0, 0]
        for i in range(4):
            pointsNX[i] = NXOpen.Point3d(points[i][0], points[i][1], points[i][2])
        lines = [0, 0, 0, 0]
        for i in range(4):
            if i != 3:
                lines[i] = workPart.Curves.CreateLine(pointsNX[i], pointsNX[i + 1])
            else:
                lines[i] = workPart.Curves.CreateLine(pointsNX[i], pointsNX[0])
        theSection = workPart.Sections.CreateSection(0.0095, 0.01, 0.5)
        originPoint = NXOpen.Point3d(0.0, 0.0, 0.0)
        createMode = NXOpen.Section.Mode.Create
        rules = []
        for i in range(4):
            rules.append(workPart.ScRuleFactory.CreateRuleBaseCurveDumb([lines[i]]))
            theSection.AddToSection([rules[i]], lines[i],
                                    NXOpen_Features.Feature.Null,
                                    NXOpen_Features.Feature.Null,
                                    originPoint,
                                    createMode,
                                    False)
        extrude_builder = workPart.Features.CreateExtrudeBuilder(NXOpen_Features.Feature.Null)
        extrude_builder.Section = theSection
        extrude_builder.Direction = workPart.Directions.CreateDirection(workPart.Points.CreatePoint(center),
                                                                        NXOpen.Vector3d(float(-normal[0]),
                                                                                        float(-normal[1]),
                                                                                        float(-normal[2])))
        extrude_builder.Limits.StartExtend.Value.RightHandSide = "0"
        extrude_builder.Limits.EndExtend.Value.RightHandSide = str(self.Size.Value)
        extrude_builder.CommitFeature()

    def prime(self, a):
        counter = 2
        flag = True
        while counter < (math.trunc(a / 2) + 1):
            if a % counter == 0:
                flag = False
            counter += 1
        return flag

    def column_quantity(self, amount):
        max_divid = 1
        counter = 2
        while counter < (math.trunc(amount / 2) + 1):
            if amount % counter == 0 and self.prime(counter) is True:
                max_divid = counter
            counter += 1
        v_quant = max_divid
        u_quant = amount / v_quant
        return u_quant, v_quant

    def length_of_segment(self, start_point, end_point):
        return ((start_point[0] - end_point[0]) ** 2 + 
                (start_point[1] - end_point[1]) ** 2 + 
                (start_point[2] - end_point[2]) ** 2) ** 0.5

    def define_points(self, tag, uv_point):
        local_ufs = NXOpen_UF.UFSession.GetUFSession()
        start_coordinates = local_ufs.Modeling.EvaluateFace(tag,
                                                            NXOpen_UF.UFConstants.UF_MODL_EVAL_UNIT_NORMAL,
                                                            uv_point)
        uv_confines = local_ufs.Modeling.AskFaceUvMinmax(tag)
        v_width = uv_confines[3] - uv_confines[2]
        u_width = uv_confines[1] - uv_confines[0]
        list_of_uv_bottom = [[uv_point[0], uv_point[1] - self.max(0.001,
                                                                  uv_point[1] / 1000)],
                             [uv_point[0], uv_point[1] + self.max(0.001,
                                                                  uv_point[1] / 1000)],
                             [uv_point[0] + self.max(0.001, uv_point[0] / 1000),
                              uv_point[1]],
                             [uv_point[0] - self.max(0.001, uv_point[0] / 1000),
                              uv_point[1]]]
        end_direction_coordinates = []
        for i in range(4):
            end_direction_coordinates.append(local_ufs.Modeling.EvaluateFace(tag,
                                                                           NXOpen_UF.UFConstants.UF_MODL_EVAL, 
                                                                           list_of_uv_bottom[i]).SrfPos)
        direction_vectors = []
        for i in range(4):
            direction_vectors.append(coordinates_dir.normalize(start_coordinates.SrfPos, end_direction_coordinates[i]))
        step_vectors = []
        for i in range(4):
            step_vectors.append(coordinates_dir.mult_const(direction_vectors[i],
                                                           self.Size.Value / 2))
        points = []
        dir1 = 0
        iterator = 0
        while dir1 < 2:
            dir2 = 2
            while dir2 < 4:
                points.append(coordinates_dir.summ(start_coordinates.SrfPos, step_vectors[dir1]))
                points[iterator] = coordinates_dir.summ(points[iterator], step_vectors[dir2])
                iterator += 1
                dir2 += 1
            dir1 += 1
        points[2], points[3] = points[3], points[2]
        return points


    def max(self, a, b):
        if a - b > 10**(-6):
            return a
        else:
            return b


    def dialogShown_cb(self):
        try:
            # ---- Enter your callback code here -----
            pass
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            self.theUI.NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))

    def get_len_from_feat(self, feat):
        """Retrieves extrude length from provided extrude feature.

        Args:
            feat (NXOpen_Features.Extrude): Extrude feature.

        Returns:
            (float):
                [2]: Retrieved length.
        """
        extrudeBuilder1 = self.work_part.Features.CreateExtrudeBuilder(feat)  # создание об класса extrudeBuilder. Что за Work_part
        start_limit = extrudeBuilder1.Limits.StartExtend.Value.Value
        end_limit = extrudeBuilder1.Limits.EndExtend.Value.Value
        return abs(end_limit - start_limit)

    def feat_width(self, tag):
        local_ufs = NXOpen_UF.UFSession.GetUFSession()
        uv_list = local_ufs.Modeling.AskFaceUvMinmax(tag)
        coordinate_min = local_ufs.Modeling.EvaluateFace(tag, NXOpen_UF.UFConstants.UF_MODL_EVAL, [uv_list[0], uv_list[2]])
        coordinate_max = local_ufs.Modeling.EvaluateFace(tag, NXOpen_UF.UFConstants.UF_MODL_EVAL, [uv_list[0], uv_list[3]])
        return self.length_of_segment(coordinate_max.SrfPos, coordinate_min.SrfPos)

    def apply_cb(self):
        try:
            ufs = NXOpen_UF.UFSession.GetUFSession()
            tags = self.face_select0.GetSelectedObjects()[0].Tag
            u_, v_ = self.column_quantity(self.Amount.Value)
            uv_list = ufs.Modeling.AskFaceUvMinmax(tags)
            u_step = (uv_list[1] - uv_list[0]) / (u_ + 1)
            v_step = (uv_list[3] - uv_list[2]) / (v_ + 1)
            u_iterator = uv_list[0] + u_step
            while u_iterator < uv_list[1]:
                v_iterator = uv_list[2] + v_step
                while v_iterator < uv_list[3]:
                    origin_points = self.define_points(tags, [u_iterator, v_iterator])
                    self.draw_block(origin_points, 
                                    ufs.Modeling.EvaluateFace(tags,
                                                              NXOpen_UF.UFConstants.UF_MODL_EVAL_UNIT_NORMAL, 
                                                              [u_iterator, v_iterator]).SrfUnormal,
                                    ufs.Modeling.EvaluateFace(tags,
                                                              NXOpen_UF.UFConstants.UF_MODL_EVAL_UNIT_NORMAL, 
                                                              [u_iterator, v_iterator]).SrfPos)
                    v_iterator += v_step
                u_iterator += u_step
            return 0
        except BaseException:
            # ---- Enter your exception handling code here -----
            self.log_infp()

    def show_info(self, msg, title=None):
        """Shows Information NX MessageBox."""
        if title is None:
            title = "Info"
        NXOpen.UI.GetUI().NXMessageBox.Show(
            title, NXOpen.NXMessageBox.DialogType.Information, msg)

    def update_cb(self, block):
        try:
            if block == self.Amount:
                # ---- Enter your code here -----
                pass
            elif block == self.Size:
                # ---- Enter your code here -----
                pass
            elif block == self.temp:
                # ---- Enter your code here -----
                pass
            elif block == self.face_select0:
                faces = self.face_select0.GetSelectedObjects()
                if len(faces) == 0:
                    return 0
                face = faces[0]
                self.show_info(str(faces))               
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            self.theUI.NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))        
        return 0


    def log_infp(self, msg=None, print_stack_explicitly=False):
        """
        Writes the whole error trace to the NX Listing Window.
        Should be included in every except: block of the code.
    
        Args:
            msg (str, optional): Optional message to output
                to the listing window.
            print_stack_explicitly (bool, optional):
    
        Returns:
            Nothing.
        """
        sep = "---------------------------------------"
        lw = NXOpen.Session.GetSession().ListingWindow
        lw.Open()
        out_str = traceback.format_exc()
        lw.WriteLine(sep)
        if msg:
            lw.WriteLine(" Bug Info: " + str(msg))
        else:
            lw.WriteLine(out_str)
        if print_stack_explicitly is True:
            lw.WriteLine("\nFull Call Stack:\n")
            for line in traceback.format_stack():
                lw.WriteLine(line.strip())
        lw.WriteLine(sep)
        lw.WriteLine("\n")
        lw.Close()

    def ok_cb(self):
        errorCode = 0
        try:
            # ---- Enter your callback code here -----
            for v in self.face_select0:
                pass
            
            errorCode = self.apply_cb()
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            errorCode = 1
            self.theUI.NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))
        
        return errorCode

    def GetBlockProperties(self, blockID):
        try:
            return self.theDialog.GetBlockProperties(blockID)
        except Exception as ex:
            # ---- Enter your exception handling code here -----
            self.theUI.NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))
        
        return None

    
def main():
    thetask = None
    try:
        thetask = task()
        #  The following method shows the dialog immediately
        thetask.Show()
    except Exception as ex:
        # ---- Enter your exception handling code here -----
        NXOpen.UI.GetUI().NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))
    finally:
        if thetask != None:
            thetask.Dispose()
            thetask = None

    
if __name__ == '__main__':
    main()

