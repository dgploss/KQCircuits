import pya
import math
import os

from kqcircuit.defaults import default_layers
from kqcircuit.pcells.kqcircuit_pcell import KQCirvuitPCell

class Swissmon(KQCirvuitPCell):
  """
  The PCell declaration for a finger capacitor
  """

  def __init__(self):
    super().__init__()    
    self.param("le1", self.TypeLayer, "Layer electron beam 1", 
      default = default_layers["Electron beam lit. 1"])      
    self.param("le2", self.TypeLayer, "Layer electron beam 2", 
      default = default_layers["Electron beam lit. 2"])
    self.param("len_direct", self.TypeDouble, "Length between the ports (um)", default = 400)
    self.param("len_finger", self.TypeDouble, "Length of the fingers (um)", default = 50)
    self.param("fingers", self.TypeInt, "Number of fingers (at least 2)", default = 3)
    self.param("arm_length", self.TypeDouble, "Arm length (um)", default = 300./2)
    self.param("arm_width", self.TypeDouble, "Arm width (um)", default = 24)
    self.param("gap_width", self.TypeDouble, "Gap width (um)", default = 24)
    self.param("corner_r", self.TypeDouble, "Corner radius (um)", default = 5)
    self.param("cpl_width", self.TypeList, "Coupler width (um, ENW)", default = [24, 24, 24])
    self.param("cpl_length", self.TypeList, "Coupler lengths (um, ENW)", default = [160, 160, 160])
    self.param("cpl_gap", self.TypeList, "Coupler gap (um, ENW)", default = [102, 102, 102])
    self.name = "qb1"

  def display_text_impl(self):
    # Provide a descriptive text for the cell
    return "swissmon({})".format(self.name)
      
  def coerce_parameters_impl(self):
    None

  def can_create_from_shape_impl(self):
    return self.shape.is_path()
  
  def parameters_from_shape_impl(self):
    None
    
  def transformation_from_shape_impl(self):
    return pya.Trans()        
    
  def produce_coupler(self, cpl_nr):
    # shortscript
    a=self.a
    w=float(self.cpl_width[cpl_nr])
    l=float(self.cpl_length[cpl_nr])
    g=float(self.cpl_gap[cpl_nr])/2
    b = self.b 
    
    # Location for connecting the waveguides to 
    port_shape = pya.DBox(-a, 0, a, b)    
    port_region = pya.Region([port_shape.to_itype(self.layout.dbu)])

    if (l>0):
      # Horseshoe upened to below
      # Refpoint in the top center
      shoe_points = [
        pya.DPoint(a, 0),
        pya.DPoint(g+w, 0),
        pya.DPoint(g+w, -l),
        pya.DPoint(g, -l),
        pya.DPoint(g, -w),
        pya.DPoint(-g, -w),
        pya.DPoint(-g, -l),
        pya.DPoint(-g-w, -l),
        pya.DPoint(-g-w, 0),      
        pya.DPoint(-a, 0)
      ]  
      shoe = pya.DPolygon(shoe_points)
      shoe.size(b)
      shoe.insert_hole(shoe_points[::-1])    
          
      # convert to range and recover CPW port
      shoe_region = pya.Region([shoe.to_itype(self.layout.dbu)])
      shoe_region.round_corners(self.corner_r, self.corner_r, self.n) 
      shoe_region2 = shoe_region - port_region
    
    # move to the north arm of swiss cross
    ground_width = (2*g - self.arm_width - 2*self.gap_width - 2*b)/2
    shift_up = self.arm_length + self.gap_width + ground_width + w + b
    transf = pya.DCplxTrans(1, 0, False, pya.DVector(0, shift_up))
    
    # rotate to the correcti direction
    rotation = [
      pya.DCplxTrans.R90, pya.DCplxTrans.R0, pya.DCplxTrans.R270
    ][cpl_nr]
    
    # draw    
    if (l>0):
      self.cell.shapes(self.layout.layer(self.lo)).insert(
        shoe_region2.transformed((rotation*transf).to_itrans(self.layout.dbu)))         
    self.cell.shapes(self.layout.layer(self.la)).insert(
      port_region.transformed((rotation*transf).to_itrans(self.layout.dbu)))
    
    # protection    
    if (l>0):
      protection = pya.DBox(-g-w-b-self.margin, -l-b-self.margin, g+w+b+self.margin, b+self.margin)
      self.cell.shapes(self.layout.layer(self.lp)).insert(protection.transformed((rotation*transf)))
      
    # add ref point
    port_ref = pya.DPoint(0,b)
    self.refpoints["cplr_port{}".format(cpl_nr)] = (rotation*transf).trans(port_ref)

  def produce_cross_and_squid(self):
    w=self.arm_width/2
    l=self.arm_length
    cross_points = [
      pya.DPoint(w, w),
      pya.DPoint(l, w),
      pya.DPoint(l, -w),
      pya.DPoint(w, -w),
      pya.DPoint(w, -l),
      pya.DPoint(-w, -l),
      pya.DPoint(-w, -w),
      pya.DPoint(-l, -w),
      pya.DPoint(-l, w),
      pya.DPoint(-w, w),
      pya.DPoint(-w, l),
      pya.DPoint(w, l),
    ] 
    
    s=self.gap_width
    f = float(self.gap_width+self.arm_width/2)/self.arm_width/2
    cross = pya.DPolygon([
              p+pya.DVector(math.copysign(s, p.x),math.copysign(s, p.y)) for p in cross_points
              ])    
    cross.insert_hole(cross_points)
    cross_rounded = cross.round_corners(self.corner_r, self.corner_r, self.n)
    #cross_rounded = cross.round_corners(self.corner_r-self.gap_width/2, self.corner_r+self.gap_width/2, self.n)
    #self.cell.shapes(self.layout.layer(self.lo)).insert(cross_rounded)
    #self.cell.shapes(self.layout.layer(self.la)).insert(cross)
    
    cross_protection = pya.DPolygon([
                        p+pya.DVector(math.copysign(s+self.margin, p.x),math.copysign(s+self.margin, p.y)) for p in cross_points
                        ])    
    self.cell.shapes(self.layout.layer(self.lp)).insert(cross_protection)
    
    
    # SQUID from template
    squid_cell =  self.layout.create_cell("SQUID", "KQCircuit")
    transf = pya.DCplxTrans(1,0,False,pya.DVector(0,-l-s-3))
    
    region_unetch = pya.Region(squid_cell.shapes(self.layout.layer(default_layers["Unetch 1"])))
    region_unetch.transform(transf.to_itrans(self.layout.dbu))
    region_etch = pya.Region([cross_rounded.to_itype(self.layout.dbu)])-region_unetch

    self.cell.shapes(self.layout.layer(self.lo)).insert(region_etch)    
    self.cell.insert(pya.DCellInstArray(squid_cell.cell_index(),transf)) 
      
  def produce_impl(self):
    
    self.produce_cross_and_squid()
    
    for i in range(3):
      self.produce_coupler(i)
      
    self.cell.refpoints = self.refpoints
    # adds annotation based on refpoints calculated above
    super().produce_impl()
    