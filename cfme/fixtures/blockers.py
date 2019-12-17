"""Collection of fixtures for simplified work with blockers.

You can use the :py:func:`blocker` fixture to retrieve any blocker
using blocker syntax (as described in :py:mod:`cfme.metaplugins.blockers`).
The :py:func:`bug` fixture is specific for bugzilla,
it accepts number argument and spits out the BUGZILLA BUG!
(a :py:class:`utils.bz.BugWrapper`, not a :py:class:`utils.blockers.BZ`!).
The :py:func:`blockers` retrieves list of all blockers
as specified in the meta marker.
All of them are converted to the :py:class:`utils.blockers.Blocker` instances
"""
import pytest

from cfme.fixtures.pytest_store import store
from cfme.utils.blockers import Blocker
from cfme.utils.blockers import BZ
from cfme.utils.blockers import GH


@pytest.fixture(scope="function")
def blocker(uses_blockers):
    """Return any blocker that matches the expression.

    Returns:
        Instance of :py:class:`utils.blockers.Blocker`
    """
    return lambda b, **kwargs: Blocker.parse(b, **kwargs)


@pytest.fixture(scope="function")
def blockers(uses_blockers, meta):
    """Returns list of all assigned blockers.

    Returns:
        List of :py:class:`utils.blockers.Blocker` instances.
    """
    return [Blocker.parse(blocker) for blocker in meta.get("blockers", [])]


@pytest.fixture(scope="function")
def bug(blocker):
    """Return bugzilla bug by its id.

    Returns:
        Instance of :py:class:`utils.bz.BugWrapper` or :py:class:`NoneType` if the bug is closed.
    """
    return lambda bug_id, **kwargs: blocker("BZ#{}".format(bug_id), **kwargs).bugzilla_bug


def pytest_addoption(parser):
    group = parser.getgroup('Blocker options')
    group.addoption(
        '--blocker-report',
        default=None,
        choices=['coverage', 'marked', 'active', 'closed'],
        dest='blocker_report',
        help='Generate a BZ report (yaml) of the given type.\n'
             'Coverage reports on automates/coverage meta markers\n'
             'Marked reports on all blockers marked on cases\n'
             'Active reports on blockers marked on cases that are currently blocking\n'
             'Closed reports on blockers that have been closed'
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """Generate a report of the blocker items (BZ's, GH, JIRA) and dump it to console

    Automatically adds collect-only option
    """
    if not config.option.blocker_report:
        return
    if not config.option.collectonly:
        config.option.collectonly = True

    tr = store.terminalreporter

    tr.write_line("Parsing testcases for blockers ...", bold=True)
    blocking = set([])
    for item in items:
        for blocker in item._metadata.get("blockers", []):
            blocker_object = Blocker.parse(blocker)
            if blocker_object.blocks:
                blocking.add(blocker_object)
    if blocking:
        tr.write_line("Marked blockers:", bold=True)
        for blocker in blocking:
            if isinstance(blocker, BZ):
                bug = blocker.bugzilla_bug
                tr = store.terminalreporter
                tr.write_line(f"- #{bug.id} - {bug.status}")
                tr.write_line(f"  {bug.summary}")
                tr.write_line(f"  {bug.version} -> {bug.target_release}")
                tr.write_line("  https://bugzilla.redhat.com/show_bug.cgi?id={bug.id}")
                tr.write_line("")  # extra space
            elif isinstance(blocker, GH):
                bug = blocker.data
                tr.write_line(f"- {bug}")
                tr.write_line(f"  {bug.title}")
            else:
                store.terminalreporter.write("- {}\n".format(str(blocker.data)))
    else:
        store.terminalreporter.write("No blockers detected!\n", bold=True)
