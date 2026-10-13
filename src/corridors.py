"""The corridors of the study, the grid regimes they sit in, and the lead case.

Ten port-hinterland corridors on four continents.  Seven follow the hinterland and
electrification rankings that guided case selection (Rotterdam, Antwerp-Bruges,
Shanghai, Ningbo-Zhoushan, Qingdao, Tianjin, Shenzhen) and the San Pedro Bay ports
(Los Angeles-Long Beach) are the reference drayage-electrification case; Jebel Ali and
Jawaharlal Nehru Port add a gas-fired Gulf grid and a coal-heavy South Asian grid.
Grid regimes are regional where the grid is (China's East, North and Southern grids;
California's CAMX subregion), national elsewhere.
"""
FOCAL = "rotterdam"
NETWORKS = ("rotterdam", "antwerp", "shanghai", "ningbo", "qingdao", "tianjin",
            "shenzhen", "sanpedrobay", "jebelali", "jnpt")
#  the distinct grid regimes, used as the columns of the corridor x regime matrix
COUNTRIES = ("Netherlands", "Belgium", "China-East", "China-North", "China-South",
             "USA-California", "UAE", "India")
