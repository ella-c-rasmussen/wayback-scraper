import setuptools as st

with open ('requirements.txt', 'r') as reqs:
    requirements = reqs.read()

st.setup(  name = 'wb-scraper',
           version = '1.0',
           description = 'Wayback Machine Scraper',
           author = 'Ella Rasmussen',
           url = 'https://github.com/ella-c-rasmussen/wayback-scraper',
           py_modules = ['wb_scraper', 'scraper_body'],
           packages = st.find_packages(),
           install_requires = [requirements],
           python_requires = '>=3.9',
           classifiers = ["Programming Language :: Python :: 3.9",
                          "Private :: Do Not Upload"],
           entry_points = ''' [console_scripts]
                              wb-scraper=wb_scraper:cli''')

