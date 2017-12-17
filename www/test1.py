#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from jinja2 import Environment,Template


Template("""\
<html>
    Hello {{ user }}
</html>
""")