# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.defaults import default_layers


class AirbridgeConnection(Element):
    """The PCell declaration of an Airbridge with tapered waveguides in both ends."""

    PARAMETERS_SCHEMA = {
        **Airbridge.PARAMETERS_SCHEMA,
        **WaveguideCoplanarTaper.PARAMETERS_SCHEMA,
        "with_side_airbridges": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "With airbridges on the sides",
            "default": True
        },
        "with_right_waveguide": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "With waveguide on right side",
            "default": True
        },
        "waveguide_separation": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Distance between waveguide center conductors",
            "default": 60,
        },
    }

    def produce_impl(self):
        taper_l = self.add_element(WaveguideCoplanarTaper, WaveguideCoplanarTaper.PARAMETERS_SCHEMA,
            a2=self.bridge_width,
            b2=self.bridge_width/self.a * self.b
        )
        taper_l_ref = self.get_refpoints(taper_l)
        taper_end_v = pya.DVector(-self.bridge_length/2-2*self.pad_length, 0)
        taper_l_inst, taper_l_ref_abs = \
            self.insert_cell(taper_l, pya.DTrans(taper_end_v-taper_l_ref["port_b"].to_v()))

        a = self.bridge_width
        b = a/self.a * self.b
        terminator_l = self.add_element(WaveguideCoplanar,
            path=pya.DPath([
                taper_end_v.to_p(),
                pya.DPoint(-self.waveguide_separation/2, 0)
            ], 10),
            a=a,
            b=b,
            term1=0,
            term2=b
        )
        self.insert_cell(terminator_l, pya.DTrans(0, 0))

        ab = self.add_element(Airbridge, Airbridge.PARAMETERS_SCHEMA)
        self.insert_cell(ab, pya.DTrans.R90)
        if self.with_side_airbridges:
            gap_between_bridges = 20
            self.insert_cell(ab, pya.DTrans(1, False, 0,  self.bridge_width + gap_between_bridges))
            self.insert_cell(ab, pya.DTrans(1, False, 0, -self.bridge_width - gap_between_bridges))

        if self.with_right_waveguide:
            taper_r = self.add_element(WaveguideCoplanarTaper, WaveguideCoplanarTaper.PARAMETERS_SCHEMA,
                a1=self.bridge_width,
                b1=self.bridge_width/self.a * self.b
            )
            taper_r_ref = self.get_refpoints(taper_r)
            taper_end_v = pya.DVector(self.bridge_length/2+2*self.pad_length, 0)
            taper_r_inst, taper_r_ref_abs = \
                self.insert_cell(taper_r, pya.DTrans(taper_end_v-taper_r_ref["port_a"].to_v()))

            terminator_r = self.add_element(WaveguideCoplanar,
                path=pya.DPath([
                    pya.DPoint(self.waveguide_separation/2, 0),
                    taper_end_v.to_p(),
                ], 10),
                a=a,
                b=b,
                term1=b,
                term2=0
            )
            self.insert_cell(terminator_r, pya.DTrans(0, 0))

        self.add_port("a", taper_l_ref_abs["port_a"])
        if self.with_right_waveguide:
            self.add_port("b", taper_r_ref_abs["port_b"])

        path_airbridge = pya.DPath([pya.DPoint(-self.waveguide_separation/2, 0),
                                    pya.DPoint(self.waveguide_separation/2, 0)], self.bridge_width)
        self.cell.shapes(self.get_layer("annotations")).insert(path_airbridge)

        # adds annotation based on refpoints calculated above
        super().produce_impl()