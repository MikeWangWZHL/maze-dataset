import math
import typing
from typing import Iterable, Literal, Mapping

import numpy as np
from jaxtyping import Bool

WhenMissing = Literal["except", "skip", "include"]


def bool_array_from_string(
    string: str, shape: list[int], true_symbol: str = "T"
) -> Bool[np.ndarray, "*shape"]:
    """Transform a string into an ndarray of bools.

    Parameters
    ----------
    string: str
        The string representation of the array
    shape: list[int]
        The shape of the resulting array
    true_symbol:
        The character to parse as True. Whitespace will be removed. All other characters will be parsed as False.

    Returns
    -------
    np.ndarray
        A ndarray with dtype bool of shape `shape`

    Examples
    --------
    >>> bool_array_from_string(
    ...     "TT TF", shape=[2,2]
    ... )
    array([[ True,  True],
        [ True, False]])
    """
    stripped = "".join(string.split())

    expected_symbol_count = math.prod(shape)
    symbol_count = len(stripped)
    if len(stripped) != expected_symbol_count:
        raise ValueError(
            f"Connection List contains the wrong number of symbols. Expected {expected_symbol_count}. Found {symbol_count} in {stripped}."
        )

    bools = [True if symbol == true_symbol else False for symbol in stripped]
    return np.array(bools).reshape(*shape)


def corner_first_ndindex(n: int, ndim: int = 2) -> list[tuple]:
    """returns an array of indices, sorted by distance from the corner

    this gives the property that `np.ndindex((n,n))` is equal to
    the first n^2 elements of `np.ndindex((n+1, n+1))`

    ```
    >>> corner_first_ndindex(1)
    [(0, 0)]
    >>> corner_first_ndindex(2)
    [(0, 0), (0, 1), (1, 0), (1, 1)]
    >>> corner_first_ndindex(3)
    [(0, 0), (0, 1), (1, 0), (1, 1), (0, 2), (2, 0), (1, 2), (2, 1), (2, 2)]
    ```
    """

    unsorted: list = list(np.ndindex(tuple([n for _ in range(ndim)])))
    return sorted(unsorted, key=lambda x: (max(x), x if x[0] % 2 == 0 else x[::-1]))

    # alternate numpy version from GPT-4:
    """
    # Create all index combinations
    indices = np.indices([n]*ndim).reshape(ndim, -1).T
    # Find the max value for each index
    max_indices = np.max(indices, axis=1)
    # Identify the odd max values
    odd_mask = max_indices % 2 != 0
    # Make a copy of indices to avoid changing the original one
    indices_copy = indices.copy()
    # Reverse the order of the coordinates for indices with odd max value
    indices_copy[odd_mask] = indices_copy[odd_mask, ::-1]
    # Sort by max index value, then by coordinates
    sorted_order = np.lexsort((*indices_copy.T, max_indices))
    return indices[sorted_order]
    """


def adj_list_to_nested_set(adj_list: list) -> set:
    """Used for comparison of adj_lists

    Adj_list looks like [[[0, 1], [1, 1]], [[0, 0], [0, 1]], ...]
    We don't care about order of coordinate pairs within
    the adj_list or coordinates within each coordinate pair."""
    return {
        frozenset([tuple(start_coord), tuple(end_coord)])
        for start_coord, end_coord in adj_list
    }


_AM_K = typing.TypeVar("_AM_K")
_AM_V = typing.TypeVar("_AM_V")


def apply_mapping(
    mapping: Mapping[_AM_K, _AM_V],
    iter: Iterable[_AM_K],
    when_missing: WhenMissing = "skip",
) -> list[_AM_V]:
    """Given an and a mapping, apply the mapping to the iterable with certain options"""
    output: list[_AM_V] = list()
    item: _AM_K
    for item in iter:
        if item in mapping:
            output.append(mapping[item])
            continue
        match when_missing:
            case "skip":
                continue
            case "include":
                output.append(item)
            case "except":
                raise ValueError(f"item {item} is missing from mapping {mapping}")
            case _:
                raise ValueError(f"invalid value for {when_missing = }")
    return output


def apply_mapping_chain(
    mapping: Mapping[_AM_K, Iterable[_AM_V]],
    iter: Iterable[_AM_K],
    when_missing: WhenMissing = "skip",
) -> list[_AM_V]:
    """Given a list and a mapping, apply the mapping to the list"""
    output: list[_AM_V] = list()
    item: _AM_K
    for item in iter:
        if item in mapping:
            output.extend(mapping[item])
            continue
        match when_missing:
            case "skip":
                continue
            case "include":
                output.append(item)
            case "except":
                raise ValueError(f"item {item} is missing from mapping {mapping}")
            case _:
                raise ValueError(f"invalid value for {when_missing = }")
    return output
