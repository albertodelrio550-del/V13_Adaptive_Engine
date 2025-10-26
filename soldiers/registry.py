import importlib
import pkgutil
from soldiers.soldier_base import SoldierBase

def load_squad(capital_map: dict = None):
    """
    Dynamically imports all Ball modules from the soldiers package
    and instantiates them.

    Args:
        capital_map (dict): optional map like {"Ball1": 500, "Ball2": 500, ...}
    Returns:
        list: list of initialized soldier objects
    """
    squad = []
    package = __package__.split('.')[0] + ".soldiers"

    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if not module_name.startswith("ball_"):
            continue
        module = importlib.import_module(f"{package}.{module_name}")
        class_name = module_name.replace("ball_", "Ball").capitalize()

        # Example: ball_1 → Ball1
        class_name = "Ball" + module_name.split("_")[1]

        cls = getattr(module, class_name)
        if issubclass(cls, SoldierBase):
            cap = 1000
            if capital_map and class_name in capital_map:
                cap = capital_map[class_name]
            soldier = cls(class_name, cap)
            squad.append(soldier)

    return squad
