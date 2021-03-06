#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of CbM (https://github.com/ec-jrc/cbm).
# Author    : Konstantinos Anastasakis
# Credits   : GTCAP Team
# Copyright : 2021 European Commission, Joint Research Centre
# License   : 3-Clause BSD


from ipywidgets import Tab
from src.ipycbm.utils import help_docs
from src.ipycbm.plugins.qa import qa_settings, qa_panel

def qa_widget_box():

    tab_box = Tab(children=[qa_panel.qa(), help_docs.widget_box(),
                  qa_settings.widget_box()])

    tab_box.set_title(0, 'Quality assessment')
    tab_box.set_title(1, 'Help')
    tab_box.set_title(2, 'Settings')

    return tab_box
