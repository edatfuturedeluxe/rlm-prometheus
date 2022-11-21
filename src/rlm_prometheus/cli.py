"""Command-line functions / entry points."""

import sys
from time import sleep

import click
from loguru import logger as log
from prometheus_client import start_http_server

from .config import get_config_from_env, load_config_file
from .metrics import RlmProductMetrics


@click.command()
@click.option("-v", "--verbose", count=True)
@click.option("--config", type=str)
def run_rlm_exporter(verbose, config):
    """Main CLI entry point for the RLM exporter. Blocking.

    Parameters
    ----------
    verbose : int
        Verbosity level for logging, ranges from 0 ("WARNING") to 3 ("TRACE").
    config : str
        A path to a configuration file. If `None` the settings will be derived
        from environment variables.
    """
    level = "WARNING"
    if verbose == 1:
        level = "INFO"
    elif verbose == 2:
        level = "DEBUG"
    elif verbose >= 3:
        level = "TRACE"
    # set up logging, loguru requires us to remove the default handler and
    # re-add a new one with the desired log-level:
    log.remove()
    log.add(sys.stderr, level=level)
    log.success(f"Configured logging level to [{level}] ({verbose}).")

    if config:
        configuration = load_config_file(config)
    else:
        configuration = get_config_from_env()

    start_http_server(configuration.exporter_port)
    metrics = RlmProductMetrics(configuration, isv="bitplane")
    log.debug(f"Starting metrics collection, interval {configuration.interval}s.")
    while True:
        log.trace("Updating pool status...")
        try:
            metrics.collector.collect()
        except Exception as err:  # pylint: disable-msg=broad-except
            log.error(f"Collecting new data failed: {err}")
        try:
            metrics.update_metrics()
        except Exception as err:  # pylint: disable-msg=broad-except
            log.error(f"Updating metrics failed: {err}")
        sleep(configuration.interval)
