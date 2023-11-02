import random

import numpy as np


def set_seed(seed: int):
    """
    Sets the seed for generating random numbers in PyTorch, numpy and Python.
    Args:
        seed (int): The desired seed value to be set.

    Returns:

    """
    random.seed(seed)
    np.random.seed(seed)

    import torch

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # os.environ["PYTHONHASHSEED"] = str(seed)
    # if deterministic_cudnn:
    #     torch.backends.cudnn.deterministic = True
    #     torch.backends.cudnn.benchmark = False
