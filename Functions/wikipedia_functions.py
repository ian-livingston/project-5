    import requests
    import re
    from bs4 import BeautifulSoup
    from tqdm import tqdm
    import pickle
    import unidecode
    import pandas as pd
    import matplotlib.pyplot as plt
    from random import randint


def get_links_from_raw_html(raw_html, url_end, area, dict_with_places=None):
    '''Takes raw html, the end of a Wiki page URL (for identifying purposes) and an area name (same) all as strings
    and returns a list of wikilink-text tuples. If dict_with_places is passed as a tuple (dictionary, included places 
    as strings), returns the dictionary with the new area, included places and links appended.
    
    Arguments: string (HTML), string (end of URL), string, bool (optional)
    Retuns: list or dictionary
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


def get_all_soups(url):
    '''Takes a single URL and returns a dictionary of Wikipedia backlinks.

    Arguments: string (URL)
    Returns:
    '''

    full_dict = {}

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page)

    page_wikilinks = list(set([f'https://en.wikipedia.org/wiki/{wikilink.text}' for wikilink in soup.find("div", id="bodyContent").find_all("a", href=re.compile("(\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))

    for wikilink in tqdm(page_wikilinks):
        response = requests.get(url)
        page = response.text
        soup = BeautifulSoup(page)

        try:
            title = soup.find(id="firstHeading").text
        except AttributeError:
            title = wikilink.split("/wiki/")[-1]
            continue
        
        links = get_wikilinks([wikilink], no_dict=True)
        full_dict[title] = (str(soup), links)
    
    return full_dict


# For getting backlinks for a list of Wikipedia URLs
def get_wikilinks(url_list, no_dict=False):
    '''Takes a list of URLs, scraped Wikipedia backlinks for each page and returns a 
    a dictionary with link (raw)-link (lean) tuples for each URL.
    
    Arguments: list of strings (URLs) bool (optional)
    Returns: dict
    '''

    dict_of_links = {}

    for url in tqdm(url_list):
        
        if url != "?":
            # First collect the HTML for the page
            response = requests.get(url)
            print(response.status_code)
            page = response.text
            soup = BeautifulSoup(page)

            # Each page should include itself in its links, as others that link to it will share something with it
            self_link = url.split("https://en.wikipedia.org/wiki/")[1]

            title = soup.find(id="firstHeading").text
            tags_to_extract = ['table', 'script', 'meta', 'style']
            titles_to_extract = ['Jump up', 'Enlarge', re.compile("(Wikipedia:)"), re.compile("Help:"), re.compile("(Category:Wiki.*)"), re.compile("(Category:Comm.*)"), re.compile("(Category:Articles.*)"), re.compile("(Category:All )"), 'ISBN (identifier)', re.compile("(Special:)"), re.compile("(Category:CS1)"), "Category:Harv and Sfn template errors", "Wayback Machine", "The World Factbook", "S2CID (identifier)", re.compile("(\(identifier\))"), "Capital city", "Curlie"]
            texts_to_extract = ['edit', re.compile("(Jump to)"), 'cuisine', re.compile("(Help:)")]
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
            page_wikilinks = [(self_link, title)] + list(set([(wikilink["href"].lstrip('/wiki/'), unidecode.unidecode(wikilink.text)) for wikilink in main_body.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))
        
            dict_of_links[title] = page_wikilinks

            if no_dict:
                return page_wikilinks

    return dict_of_links


# For getting all the text from a Wikipedia page
def get_page_text(url, with_ner=False):
    '''Takes a URL and returns all the page text and optionally named entities
    in a df.
    
    Arguments: string (URL)
    Returns: df

    '''

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page, 'lxml')
    title = soup.find(id="firstHeading").text

    # Extract the plain text content from paragraphs
    page_text = []

    for i in soup.find_all(['p','span']):
        if i.name == 'p':
            page_text.append(str(i.text))
        elif i.get("class") == ['mw-headline']:
            page_text.append(str(i.text))

    text = ' '.join(page_text)

    # Drop footnote superscripts in brackets
    text = re.sub(r"\[.*?\]+", '', text)

    # Replace '\n' (a new line) with '' and end the string at $1000.
    text = text.replace('\n', '')

    # Get links to images, just in case (later will evaluate permissions)
    images = list(set([f'https://en.wikipedia.org/wik{a["href"]}' for a in soup.find_all("a", class_="image") if a['href'] != '/wiki/File:Commons-logo.svg']))

    if with_ner == True:
        doc = nlp(text)
        named_entities = list(set([X.text for X in doc.ents if X.label_ == "GPE" or X.label_ == "LOC"]))
        return title, text, named_entities, images
    else:
        return title, text


def add_to_foods_df(url, df=foods_df, pickle=False):

    title, text, entities, images = get_page_text(url, with_ner=True)
    links = get_wikilinks([url], no_dict=True)
    df = df.append({"Food": title, "Places": entities, "Text": text, "Wikilinks": links, "Image links": images, "URL": url}, ignore_index=True)

    if pickle:
        with open("foods_df.pickle", "wb") as to_write:
            pickle.dump(foods_df, to_write)

    return df


# For actual measurement calculations
# For getting the most similar item based on cosine distance
# Inspiration and some code from Will Koehrsen (https://github.com/WillKoehrsen)
def find_similar(name, weights, index_name='country', n=10, least=False, return_dist=False, plot=False):
    '''Takes a country name as a string, an array of weights extracted from a neural network 
    and returns the n most similar items (or least) to name based on embeddings. Option to also 
    plot the results.
    
    Arguments: string, array, int (optional), bool (optional), bool (optional), bool (optional)
    Returns: (none), list (optional), string (optional)
    '''
    
    # Select index and reverse index
    if index_name == 'country':
        index = country_index
        rindex = index_country
    elif index_name == 'page':
        index = link_index
        rindex = index_link
    
    # Check to make sure `name` is in index
    try:
        # Calculate dot product between book and all others
        dists = np.dot(weights, weights[index[name]])
    except KeyError:
        print(f'{name} not found')
        return
    
    # Sort distance indexes from smallest to largest
    sorted_dists = np.argsort(dists)
    
    # Plot results if specified
    if plot:
        
        # Find furthest and closest items
        furthest = sorted_dists[:(n // 2)]
        closest = sorted_dists[-n-1: len(dists) - 1]
        items = [rindex[c] for c in furthest]
        items.extend(rindex[c] for c in closest)
        
        # Find furthest and closets distances
        distances = [dists[c] for c in furthest]
        distances.extend(dists[c] for c in closest)
        
        colors = ['r' for _ in range(n //2)]
        colors.extend('g' for _ in range(n))
        
        data = pd.DataFrame({'distance': distances}, index = items)
        
        # Horizontal bar chart
        data['distance'].plot.barh(color = colors, figsize = (10, 8),
                                   edgecolor = 'k', linewidth = 2)
        plt.xlabel('Cosine Similarity');
        plt.axvline(x = 0, color = 'k');
        
        # Formatting for italicized title
        name_str = f'{index_name.capitalize()}s Most and Least Similar to'
        for word in name.split():
            # Title uses latex for italize
            name_str += ' $\it{' + word + '}$'
        plt.title(name_str, x = 0.2, size = 28, y = 1.05)
        
        return None
    
    # If specified, find the least similar
    if least:
        # Take the first n from sorted distances
        closest = sorted_dists[:n]
         
        print(f'{index_name.capitalize()}s furthest from {name}:\n')
        
    # Otherwise find the most similar
    else:
        # Take the last n sorted distances
        closest = sorted_dists[-n:]
        
        # Need distances later on
        if return_dist:
            return dists, closest
        print(f'Countries closest to {name}.\n')
        
    # Need distances later on
    if return_dist:
        return dists, closest[:10]
        
    # Print formatting
    max_width = max([len(rindex[c]) for c in closest])
    
    # Print the most similar and distances
    for c in reversed(closest):
        print(f'Countries: {rindex[c]:{max_width + 2}} Similarity: {dists[c]:.{2}}')


# For getting Wikipedia backlinks from any Wikipedia page (this may overlpa with function up top)
def get_cuisine_dict(list_of_templates):
    '''Takes a list of Wikipedia Template pages for countries, collects URLs, scrapes
    data from those pages, and returns a dictionary with country names as keys and
    scraped data as values.
    
    Arguments: list (of template URLs)
    Returns: dict
    '''
 
    cuisine_dict = {}
    for group in list_of_templates:
        if group == africa_templates:
            continent = "Africa"
        elif group == middle_east_templates:
            continent = "Middle East"
        elif group == asia_templates:
            continent = "Asia"
        elif group == europe_templates:
            continent = "Europe"
        elif group == north_america_templates:
            continent = "North America"
        elif group == oceania_templates:
            continent = "Oceania"
        elif group == south_america_templates:
            continent = "South America"
        elif group == central_america_templates:
            continent = "Central America"
        elif group == caribbean_templates:
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


# For getting Wikipedia backlinks from any Wikipedia page returned as a list plus more
def get_cuisine_links(url, country, bottom_nav_check=False, text_only=False, raw_text=False, dict_with_places=None):
    '''Takes a URL, a country name as string, three optional bools, and one optional 
    dictionary and returns a list or a dictionary.
    
    Arguments: string,string, bool (optional), bool (optional), bool (optional), dict (optional)
    Returns: list, list (optional), dictionary (optional)
    '''

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


# For comparing two places/Wikipedia pages based on overlapping Wikipedia backlinks
def city_compare(names, soups, print_all=True):
    '''Takes a list of place names (strings), scrapes corresponding page soups 
    and returns a dictionary with place names as keys and the number of backlinks 
    shared with each other place as values.

    Arguments: list of strings, list of strings, bool (optional)
    Returns: dict
    '''
    
    main_dict = dict(zip(names, soups))
    best_matches = {}

    for city, links in main_dict.items():
        if print_all==True:
            print(f'\n{city}\n***********\n')
        best_score = 0
        closest_city = ''
        for other_city in main_dict.keys():
            if other_city != city:
                score = compare_places(main_dict[city], main_dict[other_city])
                if print_all==True:
                    print(f'{city} x {other_city}: {score}')
                if score > best_score:
                    best_score = score
                    closest_city = other_city
        if print_all==True:
            print(f'* CLOSEST MATCH, {city.upper()}: {closest_city.upper()} *')
        best_matches[city] = (closest_city, best_score)

    return best_matches


# For getting the backlinks from a Wikipedia page (this may overlap with function above)
def get_wiki_page(url, wikilinks=False):
    '''Takes a URL as a string, collects and parses the HTML using Beautiful Soup 
    and returns either the parsed soup or a list of backlinks as strings.

    Arguments: string (URL)
    Returns: list of strings OR parsed HTML as string
    '''

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page)

    if wikilinks==True:
        page_wikilinks = list(set([wikilink.text for wikilink in soup.find("div", id="bodyContent").find_all("a", href=re.compile("(\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))
        return page_wikilinks
    else:
        return soup

    
# For comparing two places/Wikipedia pages based on overlapping Wikipedia backlinks    
def compare_places(place1_links, place2_links):
    '''Takes two lists of formatted backlinks (strings) and returns the number of wikiilnks shared betweeen them.

    Arguments: list of strings, list of strings
    Returns: int
    '''

    counter = 0
    for link in place1_links:
        if link in place2_links:
            counter += 1

    return counter


# For pulling several different documents (as options) for each dish in the df
def process_full_df(df):
    '''Takes a full df with specific columns and returns a new df with several new columns including 
    cleaned lemmatized text.
    
    Arguments: df
    Returns: df
    '''

    named_entities = []
    lemmatized_text = []
    unidecoded_lemmatized = []
    categories = []
    place_of_origin = []
    ingredients = []
    all_food_types = []
    just_lowercase = []
    all_together = []

    for i in tqdm(range(df.shape[0])):
        see_also_removed = big_foods_df.iloc[i]["Text"].split("See also")[0].strip()
        cleaned = re.sub("(  )( *)", " ", see_also_removed)
        cleaned = re.sub("(--)", "", see_also_removed)
        doc = nlp(cleaned)

        entities = [X.text.lower() for X in doc.ents if X.label_ == "GPE" or X.label_ == "LOC" if "the" in X.text or X.text[0] != X.text[0].lower()]
        if len(entities) > 0:
            new_entities = []
            for entity in entities:
                if entity.split(" ")[0].strip() == "the":
                    new_entity = " ".join(entity.split(" ")[1:]).strip()
                    new_entities.append(new_entity)
                else:
                    new_entities.append(entity)
            entities = new_entities

        lemmatized = " ".join([token.lemma_ for token in doc if token.pos_ in ["PROPN", "VERB", "NOUN", "ADJ"] and token.is_stop == False and token.lemma_ != " "]).lower()
        lemmatized = re.sub("(  )( *)", " ", lemmatized)
        lemmatized = re.sub("( / | ― )", " ", lemmatized)
        lemmatized = re.sub("( (\d+) )", " ", lemmatized)
        lemmatized = re.sub("( ([A-z]) )", " ", lemmatized)
        lemmatized = re.sub("(\.)", " ", lemmatized)
        lemmatized_text.append(lemmatized)
        unidecoded = unidecode.unidecode(lemmatized)
        unidecoded_lemmatized.append(unidecoded)

        lower_case = " ".join([unidecode.unidecode(token.text.lower()) for token in doc if token.pos_ in ["PROPN", "VERB", "NOUN", "ADJ"] and token.is_stop == False and token.lemma_ != " "]).lower()
        lower_case = re.sub("(  )( *)", " ", lower_case)
        lower_case = re.sub("( / | ― )", " ", lower_case)
        lower_case = re.sub("( (\d+) )", " ", lower_case)
        lower_case = re.sub("( ([A-z]) )", " ", lower_case)
        lower_case = re.sub("(\.)", " ", lower_case)
        just_lowercase.append(lower_case)
        lower_case = [lower_case]
    
        links = big_foods_df.iloc[i]["Wikilinks raw"]
        cats = []
        for item in links:
            try:
                if re.match("(Category:)", item):
                    cat = item.split(":")[1].lower()
                    cat = re.sub("(_)", " ", cat)
                    cats.append(cat)
                    lower_case.append(cat)
                if re.match("(List_of_)", item):
                    cat = item.split("List_of_")[1].lower()
                    cat = re.sub("(_)", " ", cat)
                    cats.append(cat)
                    lower_case.append(cat)
            except TypeError:
                print(f'TypeError at iloc {i}')
                break

        if type(big_foods_df.iloc[i]["Infobox"]) != float:
            origin = np.NaN
            ingreds = np.NaN
            food_type = np.NaN
            for item in big_foods_df.iloc[i]["Infobox"]:
                if re.match("(Place of origin: )", item):
                    origin = re.sub("Place of origin:", "", item)
                    origin = origin.lower().strip()
                    origin = re.sub("( ?)(\((.*)\)|\[(.*)\])", "", origin)
                    origin = re.sub("(Disputed:( ?))", "", origin)
                    entities.append(origin)
                    break
            place_of_origin.append(origin)
            for item in big_foods_df.iloc[i]["Infobox"]:
                if re.match("((.*)ingredients:( *)|(.*)Ingredients:( *))", item):
                    ingreds = re.sub("((.*)ingredients:( *)|(.*)Ingredients:( *))", "", item)
                    ingreds = ingreds.lower().strip()
                    lower_case.append(ingreds)
                    break
            ingredients.append(ingreds)
            for item in big_foods_df.iloc[i]["Infobox"]:
                if re.match("((.*)type:( *)|(.*)Type:( *))", item):
                    food_type = re.sub("((.*)type:( *)|(.*)Type:( *))", "", item)
                    food_type = food_type.lower().strip()
                    lower_case.append(food_type)
                    break
            all_food_types.append(food_type)
        else:
            place_of_origin.append(np.NaN)
            ingredients.append(np.NaN)
            all_food_types.append(np.NaN)
        
        true_cat = big_foods_df.iloc[i]["Category"].lower()
        cats.append(true_cat)
        categories.append(cats)
        lower_case.append(true_cat)

        named_entities.append(entities)
        lower_case.extend(entities)
        
        all_together.append(" ".join(lower_case))
    
    df["All together"] = all_together
    df["Text: lower case"] = just_lowercase
    df["Text: lemmatized"] = lemmatized_text
    df["Text: lemmatized and unidecoded"] = unidecoded_lemmatized
    df["All places"] = named_entities
    df["Origin"] = place_of_origin
    df["Wiki categories"] = categories
    df["Main ingredients"] = ingredients
    df["Type"] = all_food_types

    with open("Processed_foods_df.pickle", "wb") as to_write:
        pickle.dump(df, to_write)
    
    return df


# For collecting geography/regional/cultural terms only
def places_clean(input_list):
    '''Takes a list of places and returns a summed, cleaned list of places in that list.
    
    Arguments: list
    Returns: list
    '''

    places_list = list(set(input_list))
    new_places = []
    for place in places_list:
        if place not in ["st. patrick's day", "easter"]:
            doc = nlp(place)
            new_place = ""
            for item in doc:
                new_item = item.lemma_
                new_item = re.sub("('s$)", "", new_item)
                if new_item != "-PRON-":
                    new_place += " " + new_item
            if new_place.strip() != "":
                new_place = re.sub("(\.)", " ", new_place)
                new_place = re.sub("(  )( *)", " ", new_place)
                new_place = unidecode.unidecode(new_place)
                new_places.append(new_place.strip())
    
    return list(set(new_places))


# For cleaning ingredient text
def ingredients_clean(text):
    '''Takes a string of text anad returns a clean version of the string.
    
    Arguments: string
    Returns: string
    '''
    
    
    stopwords = ENGLISH_STOP_WORDS
    ingredients_list = []

    text = ", ".join(text.split("("))
    text = ", ".join(text.split(")"))
    text = ", ".join(text.split(" or "))
    text = ", ".join(text.split(" and "))
    for item in text.split(","):
        if item != "" and item != " ":
            new_item = item.strip()
            for word in new_item.split(" "):
                if word.strip() in stopwords or word.strip() == "usually" or word.strip() == "often":
                    new_item = " ".join(new_item.split(word)).strip()
                    new_item = re.sub("(  )( *)", " ", new_item)
            ingredients_list.append(new_item)

    # for item in text.split(","):
    #     if re.match("((.*)\(.*\)(.*))", item):
    #         item = ", ".join(item.split("("))
    #         item = ", ".join(item.split(")"))
    #         item = [piece.strip() for piece in item.split(",") if piece.strip() != "" and piece.strip() != " "]
    #         ingredients_list.extend(item)
    #     else:
    #         ingredients_list.append(item.strip())
    
    return ingredients_list


# For a quick look look at a random dish
def get_random_dish_page():
    '''Takes no argument and returns the text of a random dish in the dataset.
    
    Arguments: (none)
    Returns: int, string
    '''
    
    x = randint(0, processed_foods_df.shape[0])

    print(processed_foods_df.iloc[x]["Food"], "\n")
    print(processed_foods_df.iloc[x]["All together"], "\n")
    
    return x, processed_foods_df.iloc[x]["All together"]


# For looking at the kinds of words included in each document
def get_random_keywords():
    '''Takes no argument and returns categorized words from a randomly generated dish.
    
    Arguments: (none)
    Returns: (none)
    '''

    x, text = get_random_dish_page()
    food_keywords = []
    geographical_keywords = []
    flavor_keywords = []
    type_keywords = []
    for term in combined_glossary:
        if term in text:
            food_keywords.append(term)
    for term in geographical_glossary:    
        if term in text:
            geographical_keywords.append(term)
    if type(processed_foods_df.iloc[x]["Origin"]) != float:
        geographical_keywords.append(processed_foods_df.iloc[x]["Origin"])
    for term in flavor_glossary:
        if term in text:
            flavor_keywords.append(term)
    for term in type_glossary:
        if term in text:
            type_keywords.append(term)

    print("\n\n==========\nFOOD:\n==========\n")
    checker = []
    for word in get_grams(text, 4):
        if word in set(food_keywords):
            checker.append(word)
    for word in set(checker):
        print(word)
    print("\n\n==========\nGEOGRAPHICAL:\n==========\n")
    for word in set(geographical_keywords):
        print(word)
    print("\n\n==========\FLAVOR:\n==========\n")
    for word in set(flavor_keywords):
        print(word)
    print("\n\n==========\nTYPE:\n==========\n")
    for word in set(type_keywords):
        print(word)
        
        
# For getting image links from Wikipedia for dishes
def get_image_urls(input_list):
    '''Takes a list of page URLs and returns a list of image URLs.
    
    Arguments: list
    Returns: list
    '''
    
    real_image_urls =[]
    for item in input_list:
        response = requests.get(item)
        if response.status_code == 200:  
            page = response.text
            soup = BeautifulSoup(page)
            image_link = soup.find(class_="fullImageLink").find("a")["href"]
            if image_link != "//upload.wikimedia.org/wikipedia/commons/d/df/Wikibooks-logo-en-noslogan.svg" and image_link != "//upload.wikimedia.org/wikipedia/commons/d/d6/Foodlogo2.svg":
                real_image_urls.append(image_link)
        if len(real_image_urls) >= 3:
            break

    return real_image_urls


# For trimming a document down 1-grams, if a pinch
def condense_list(term_list):
    '''Takes a list of words/terms and returns a joined version of the cleaned words/terms as
    a tring.
    
    Arguments: list
    Returns: string
    '''

    new_corpus = []
    for term in term_list:
        term_no_spaces = re.sub("( )", "", term)
        term_no_spaces = re.sub("(;)", " ", term_no_spaces)
        term_no_spaces = re.sub("(,)", " ", term_no_spaces)
        term_no_spaces = re.sub("(\.)", " ", term_no_spaces)
        term_no_spaces = re.sub("(=)", " ", term_no_spaces)
        term_no_spaces = re.sub("(  )( *)", " ", term_no_spaces)
        new_corpus.append(unidecode.unidecode(term_no_spaces.strip()))
    
    new_corpus = " ".join(new_corpus)

    return new_corpus