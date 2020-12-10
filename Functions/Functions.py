import requests
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
import pickle
import unidecode


def get_cuisine_links(url, country, bottom_nav_check=False, text_only=False, raw_text=False, dict_with_places=None):

    import requests
    import re
    from bs4 import BeautifulSoup
    from tqdm import tqdm
    import pickle
    import unidecode

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page)

    # Each page should include itself in its links, as others that link to it will share something with it
    self_link = url.split("https://en.wikipedia.org/wiki/")[1]
    title = soup.find(id="firstHeading").text
    bottom_nav_links = np.NaN
    if bottom_nav_check==True:
        for i, a in enumerate(soup.find_all("a", class_="mw-selflink selflink")):
            if a.text == f'Cuisine of {country}' or a.text == title:
                bottom_nav_links = []
                print(a.text)
                try:
                    for _ in soup.find(id="External_links").find_next("td", class_="navbox-list").find_all("a"):
                        bottom_nav_links.append((_["href"].lstrip('/wiki/'), _.text))
                except (AttributeError, KeyError) as error:
                    continue
                bottom_nav_links = list(set(bottom_nav_links))

    tags_to_extract = ['table', 'script', 'meta', 'style']
    titles_to_extract = ['Jump up', 'Enlarge', re.compile("(Wikipedia:)"), "Help:Category", re.compile("(Category:Wiki.*)"), re.compile("(Category:Comm.*)"), re.compile("(Category:Articles.*)"), re.compile("(Category:All )"), 'ISBN (identifier)', re.compile("(Special:)"), re.compile("(Category:CS1)")]
    texts_to_extract = ['edit', re.compile("(Jump to)"), 'cuisine']
    classes_to_extract = ['reference']
    ids_to_extract = ['mw-hidden-catlinks']

    for t in tags_to_extract:
        [s.extract() for s in soup(t)]
    for t in ids_to_extract:
        [s.extract() for s in soup(id=t)]
    for t in titles_to_extract:
        [s.extract() for s in soup("a", title=t)]
    for t in texts_to_extract:
        [s.extract() for s in soup("a", text=t)]
    for t in classes_to_extract:
        [s.extract() for s in soup("a", class_=t)]

    main_body = soup.find('div', id='bodyContent')
    if text_only==False:
        page_wikilinks = [(country, country), (self_link, title)] + list(set([(wikilink["href"].lstrip('/wiki/'), wikilink.text) for wikilink in main_body.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))
    else:
        page_wikilinks = [(country, country), (self_link, title)] + list(set([unidecode.unidecode(wikilink.text) for wikilink in main_body.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))

    if dict_with_places:
        dictionary = dict_with_places[0]
        places = dict_with_places[1]
        dictionary = dictionary.append(pd.DataFrame.from_dict({country: [places, page_wikilinks]}, orient='index', columns=["Places", "Links"]))
        return dictionary
    
    if bottom_nav_check==True:
        return page_wikilinks, bottom_nav_links
    else:
        return page_wikilinks


def get_links_from_raw_html(raw_html, url_end, area, dict_with_places=None):
    '''Takes raw html, the end of a Wiki page URL (for identifying purposes) and an area name (same) all as strings
    and returns a list of wikilink-text tuples. If dict_with_places is passed as a tuple (dictionary, included places 
    as strings), returns the dictionary with the new area, included places and links appended.
    '''

    soup = BeautifulSoup(raw_html)

    tags_to_extract = ['table', 'script', 'meta', 'style']
    titles_to_extract = ['Jump up', 'Enlarge', re.compile("(Wikipedia:)"), "Help:Category", re.compile("(Category:Wiki.*)"), re.compile("(Category:Comm.*)"), re.compile("(Category:Articles.*)"), re.compile("(Category:All )"), 'ISBN (identifier)', re.compile("(Special:)"), re.compile("(Category:CS1)")]
    texts_to_extract = ['edit', re.compile("(Jump to)")]
    classes_to_extract = ['reference']
    ids_to_extract = ['mw-hidden-catlinks']

    for t in tags_to_extract:
        [s.extract() for s in soup(t)]
    for t in ids_to_extract:
        [s.extract() for s in soup(id=t)]
    for t in titles_to_extract:
        [s.extract() for s in soup("a", title=t)]
    for t in texts_to_extract:
        [s.extract() for s in soup("a", text=t)]
    for t in classes_to_extract:
        [s.extract() for s in soup("a", class_=t)]

    links = [(url_end, area)] + list(set([(wikilink["href"].lstrip('/wiki/'), wikilink.text) for wikilink in soup.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))

    if dict_with_places:
        dictionary = dict_with_places[0]
        places = dict_with_places[1]
        dictionary = dictionary.append(pd.DataFrame.from_dict({links[0][1]: [places, links]}, orient='index', columns=["Places", "Links"]))
        return dictionary
    else:
        return links



def get_cuisine_dict(list_of_templates, kenya_links, zimbabwe_links, jersey_links, cook_islands_links, tonga_links, st_kitts_links, martinique_links, wallis_and_futuna_links):
 
    cuisine_dict = {}
    for group in list_of_templates:
        if group == list_of_templates[0]:
            continent = "Africa"
        elif group == list_of_templates[1]:
            continent = "Middle East"
        elif group == list_of_templates[2]:
            continent = "Asia"
        elif group == list_of_templates[3]:
            continent = "Europe"
        elif group == list_of_templates[4]:
            continent = "North America"
        elif group == list_of_templates[5]:
            continent = "Oceania"
        elif group == list_of_templates[6]:
            continent = "South America"
        elif group == list_of_templates[7]:
            continent = "Central America"
        elif group == list_of_templates[8]:
            continent = "Caribbean"
        for template in group:
            country = " ".join(template[0].split(":")[1].split(" ")[:-1])
            response = requests.get(f'{template[1]}')
            page = response.text
            soup = BeautifulSoup(page)
            if country == "Balearic Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Balearic_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bosnia and Herzegovina":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bosnia_and_Herzegovina_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Canary Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Canarian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Angola":
                cuisine_link = 'https://en.wikipedia.org/wiki/Angolan_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Burundi":
                cuisine_link = 'https://en.wikipedia.org/wiki/Burundian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Chad":
                cuisine_link = 'https://en.wikipedia.org/wiki/Chadian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Comoros" or country == "Madagascar":
                cuisine_link = 'https://en.wikipedia.org/wiki/Malagasy_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Comoros" or country == "Madagascar":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Eswatini'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Djiboutii":
                cuisine_link = 'https://en.wikipedia.org/wiki/Djiboutian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Gabon":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gabonese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Gambia":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gambian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Ivory Coast":
                cuisine_link = 'https://en.wikipedia.org/wiki/Ivorian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Kenya":
                country_links = kenya_links
                bottom_links = np.NaN
            elif country == "Lesotho":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Lesotho'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Libya":
                cuisine_link = 'https://en.wikipedia.org/wiki/Libyan_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Malawi":
                cuisine_link = 'https://en.wikipedia.org/wiki/Malawian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mauritania":
                cuisine_link = 'https://en.wikipedia.org/wiki/Mauritanian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mauritania":
                cuisine_link = 'https://en.wikipedia.org/wiki/Mauritanian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mauritius":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Mauritius'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mozambique":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Mozambique'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Niger":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Niger'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Réunion":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gastronomy_of_Reuni%C3%B3n'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Réunion":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gastronomy_of_Reuni%C3%B3n'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "São Tomé and Príncipe":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_S%C3%A3o_Tom%C3%A9_and_Pr%C3%ADncipe'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Seychelles":
                cuisine_link = 'https://en.wikipedia.org/wiki/Seychellois_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "South Sudan":
                cuisine_link = 'https://en.wikipedia.org/wiki/South_Sudanese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Sudan":
                cuisine_link = 'https://en.wikipedia.org/wiki/Sudanese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Togo":
                cuisine_link = 'https://en.wikipedia.org/wiki/Togolese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Zambia":
                cuisine_link = 'https://en.wikipedia.org/wiki/Zambian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Zimbabwe":
                country_links = zimbabwe_links
                bottom_links = np.NaN
            elif country == "Iraqi Kurdistan":
                cuisine_link = 'https://en.wikipedia.org/wiki/Kurdish_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "South India":
                cuisine_link = 'https://en.wikipedia.org/wiki/South_Indian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Korea":
                cuisine_link = 'https://en.wikipedia.org/wiki/Korean_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Crimea":
                cuisine_link = 'https://en.wikipedia.org/wiki/Crimean_Tatar_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Jersey":
                country_links = jersey_links
                bottom_links = np.NaN
            elif country == "Liechtenstein":
                cuisine_link = 'https://en.wikipedia.org/wiki/Liechtenstein_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Northern Ireland":
                cuisine_link = 'https://en.wikipedia.org/wiki/Northern_Irish_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Poland":
                cuisine_link = 'https://en.wikipedia.org/wiki/Polish_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Wales":
                cuisine_link = 'https://en.wikipedia.org/wiki/Welsh_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bermuda":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bermudian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bermuda":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bermudian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Cook Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
                country_links = country_links + cook_islands_links
            elif country == "Federated States of Micronesia":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Mariana_Islands' #This may need to be changed
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Fiji":
                cuisine_link = 'https://en.wikipedia.org/wiki/Fijian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "French Polynesia":
                cuisine_link1 = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here
                country_links1, bottom_links = get_cuisine_links(cuisine_link1, country, bottom_nav_check=True)
                cuisine_link2 = 'https://en.wikipedia.org/wiki/Po%27e' #Specific dish, added because there isn't much here
                country_links2, bottom_links = get_cuisine_links(cuisine_link2, country, bottom_nav_check=True)
                country_links = country_links1 + country_links2
            elif country == "Nauru":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Nauru'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True) 
            elif country == "Papua New Guinea":
                cuisine_link = 'https://en.wikipedia.org/wiki/Papua_New_Guinean_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)   
            elif country == "Samoa":
                cuisine_link = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Tonga":
                cuisine_link = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here (also Tonga included here and I've already refered to it)
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
                country_links = country_links + tonga_links
            elif country == "Tuvalu":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Tuvalu'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "The Bahamas":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bahamian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Saint Kitts and Nevis":
                country_links = st_kitts_links
                bottom_links = np.NaN
            elif country == "Martinique":
                country_links = martinique_links
                bottom_links = np.NaN
            elif country == "Turks and Caicos":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Turks_and_Caicos_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Wallis and Futuna":
                country_links = wallis_and_futuna_links
                bottom_links = np.NaN
            elif country == "Rapa Nui":
                cuisine_link = 'https://en.wikipedia.org/wiki/Pascuense_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Christmas Island":
                cuisine_link = 'https://en.wikipedia.org/wiki/Christmas_Island_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mariana Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Mariana_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Niue":
                cuisine_link = 'https://en.wikipedia.org/wiki/Niuean_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bouvet Island":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bouvet_Island'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "South Georgia and the South Sandwich Islands topics":
                cuisine_link = 'https://en.wikipedia.org/wiki/South_Georgia_and_the_South_Sandwich_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Eswatini":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Eswatini'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Djibouti":
                cuisine_link = 'https://en.wikipedia.org/wiki/Djiboutian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Marshall Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Marshallese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Cayman Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Cayman_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)

            else:
                country_links, bottom_links = np.NaN, np.NaN
                for a in soup.find("div", class_="navbox").find_all("a"):
                    if a.text == "Cuisine":
                        cuisine_link = f'https://en.wikipedia.org{a["href"]}'
                        country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
                
            cuisine_dict[country] = continent, country_links, bottom_links
    
    return cuisine_dict