import click
from scraper_body import scraper

@click.group()
def cli():
    pass

# Enter a URL from the command line.
@cli.command()
@click.option('-u', '--url', type = str, required = True, help = 'Exact URL')
def scrape(url):
    scraper.wayback_scrape(url)