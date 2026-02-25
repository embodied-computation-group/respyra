"""Response collection and event logging helpers.

Thin wrappers around PsychoPy's event module that standardise the return
format and provide a simple event-log accumulator.
"""

from psychopy import event


def check_keys(key_list=None, clock=None):
    """Non-blocking check for keypresses.

    Parameters
    ----------
    key_list : list of str or None
        Keys to listen for.  ``None`` accepts any key.
    clock : psychopy.core.Clock or None
        If provided, return reaction times relative to this clock.

    Returns
    -------
    list of (str, float)
        Each element is ``(key_name, timestamp)``.  The list is empty if
        nothing was pressed.  When *clock* is ``None`` the timestamp comes
        from PsychoPy's default monotonic clock.
    """
    keys = event.getKeys(keyList=key_list, timeStamped=clock or True)
    # getKeys with timeStamped returns list of [key, time] sub-lists
    return [(k, t) for k, t in keys]


def wait_for_key(key_list=None, clock=None, max_wait=float("inf")):
    """Block until a key is pressed (or *max_wait* seconds elapse).

    Parameters
    ----------
    key_list : list of str or None
        Acceptable keys.  ``None`` accepts any key.
    clock : psychopy.core.Clock or None
        Clock for reaction-time stamping.
    max_wait : float
        Maximum seconds to wait.  Defaults to infinity.

    Returns
    -------
    tuple of (str, float) or None
        ``(key_name, timestamp)`` for the first key pressed, or ``None``
        if *max_wait* elapsed with no response.
    """
    keys = event.waitKeys(
        maxWait=max_wait,
        keyList=key_list,
        timeStamped=clock or True,
    )
    if keys is None:
        return None
    return (keys[0][0], keys[0][1])


def record_event(event_log, event_type, timestamp, **data):
    """Append a timestamped event dict to *event_log*.

    Parameters
    ----------
    event_log : list
        Mutable list that accumulates event records.
    event_type : str
        Label for this event (e.g. ``'trial_start'``, ``'response'``).
    timestamp : float
        Time of the event (typically from a ``core.Clock``).
    **data
        Arbitrary extra fields merged into the record.
    """
    event_log.append(
        {
            "event_type": event_type,
            "timestamp": timestamp,
            **data,
        }
    )
