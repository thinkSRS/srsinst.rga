##! 
##! Coptright(c) 2022, 2023 Stanford Research Systems, All right reserved
##! Subject to the MIT License
##! 

import logging
from srsgui import Task
from srsinst.rga.instruments.rga100.rga import RGA100

logger = logging.getLogger(__name__)


def get_rga(task: Task, name=None) -> RGA100:
    """
    Instead of using Task.get_instrument() in a Task subclass directly,
    Defining a wrapper function that returns an instrument of
    a specific class will help a context-sensitive editors
    to display  attributes available for the instrument class.
    """

    if name is None:
        inst = list(task.inst_dict.values())[0]
    else:
        inst = task.get_instrument(name)

    if issubclass(type(inst), RGA100):
        return inst
    else:
        logger.error('{} is not {}'.format(type(inst), RGA100))
        return None
