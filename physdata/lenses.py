"""List of spherical lens data. Keys are manufacturer, type (e.g. plano-convex),
material (e.g. CaF2, N-BK7), diameter in mm, nominal focal length in mm.
Values are (ROC 1, thickness, ROC 2).
"""
inf=float('inf')
spherical=\
    {'Thorlabs':
        {'plano-convex':
            {'CaF2':
                {25.4:
                    {50:(21.7,6.1,inf),75:(32.5,4.6,inf),100:(43.4,3.9,inf),1000:(433.9,2.2,inf)},
                'rii':{'book':'CaF2'},
                },
            'N-BK7':
                {25.4:
                    {50:(25.8,5.3,inf),75:(38.6,4.1,0),100:(51.5,3.6,inf),1000:(515.1,2.2,inf)},
                'rii':{'book':'BK7','page':'SCHOTT'}
                },
            'UVFS':
                {25.4:
                    {50:(23,5.8,inf),75:(34.5,4.4,inf),100:(46,3.8,inf),1000:(460.1,2.2,inf)},
                'rii':{'book':'SiO2'}
                }
            }
        }
    }
