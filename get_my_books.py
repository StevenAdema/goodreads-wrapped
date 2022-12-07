import argparse
from datetime import datetime
import json
import os
import re
import time
from urllib.request import urlopen
from urllib.error import HTTPError
import bs4
import pandas as pd
from collections import Counter

class BookData():
    
    def __init__(self, userid):
        self.userid = str(userid)
        self.df = pd.DataFrame()
        self.data_dir = './' + self.userid
        self.data_dir_all = './' + self.userid + '/all_books.csv'
        self.data_dir_read = './' + self.userid + '/read_this_year.csv'
        isExist = os.path.exists(self.data_dir)
        if not isExist:
            os.makedirs(self.data_dir)

        start_time = datetime.now()
        script_name = os.path.basename(__file__)

        parser = argparse.ArgumentParser()
        parser.add_argument('--user_id', default=self.userid, type=str)
        parser.add_argument('--book_ids_path', default='my_books.txt', type=str)
        parser.add_argument('--output_directory_path', default=self.userid,type=str)
        parser.add_argument('--format', type=str, action="store", default="csv",
                            dest="format", choices=["json", "csv"],
                            help="set file output format")
        args = parser.parse_args()

        self.create_book_list(args.user_id)
        book_ids              = [line.strip() for line in open(args.book_ids_path, 'r') if line.strip()]
        books_already_scraped =  [file_name.replace('_book-metadata.json', '') for file_name in os.listdir(args.output_directory_path) if file_name.endswith('.json') and not file_name.startswith('all_books')]
        books_to_scrape       = [book_id for book_id in book_ids if book_id not in books_already_scraped]
        condensed_books_path   = args.output_directory_path + '/all_books'

        for i, book_id in enumerate(books_to_scrape):
            try:
                print(str(datetime.now()) + ' ' + script_name + ': Scraping ' + book_id + '...')
                print(str(datetime.now()) + ' ' + script_name + ': #' + str(i+1+len(books_already_scraped)) + ' out of ' + str(len(book_ids)) + ' books')

                book = self.scrape_book(book_id)
                # Add book metadata to file name to be more specific
                json.dump(book, open(args.output_directory_path + '/' + book_id + '_book-metadata.json', 'w'))

                print('=============================')

            except HTTPError as e:
                print(e)
                exit(0)

        books = self.condense_books(args.output_directory_path)
        if args.format == 'json':
            json.dump(books, open(f"{condensed_books_path}.json", 'w'))
        elif args.format == 'csv':
            json.dump(books, open(f"{condensed_books_path}.json", 'w'))
            book_df = pd.read_json(f"{condensed_books_path}.json")
            book_df.to_csv(f"{condensed_books_path}.csv", index=False, encoding='utf-8')
            
        print(str(datetime.now()) + ' ' + script_name + f':\n\n🎉 Success! All book metadata scraped. 🎉\n\nMetadata files have been output to /{args.output_directory_path}\nGoodreads scraping run time = ⏰ ' + str(datetime.now() - start_time) + ' ⏰') 
        self.df = pd.read_csv(self.data_dir_all)


    def get_all_lists(self, soup):

        lists = []
        list_count_dict = {}

        if soup.find('a', text='More lists with this book...'):

            lists_url = soup.find('a', text='More lists with this book...')['href']

            source = urlopen('https://www.goodreads.com' + lists_url)
            soup = bs4.BeautifulSoup(source, 'lxml')
            lists += [' '.join(node.text.strip().split()) for node in soup.find_all('div', {'class': 'cell'})]

            i = 0
            while soup.find('a', {'class': 'next_page'}) and i <= 10:

                time.sleep(1) # original value: 1
                next_url = 'https://www.goodreads.com' + soup.find('a', {'class': 'next_page'})['href']
                source = urlopen(next_url)
                soup = bs4.BeautifulSoup(source, 'lxml')

                lists += [node.text for node in soup.find_all('div', {'class': 'cell'})]
                i += 1

            # Format lists text.
            for _list in lists:
                # _list_name = ' '.join(_list.split()[:-8])
                # _list_rank = int(_list.split()[-8][:-2]) 
                # _num_books_on_list = int(_list.split()[-5].replace(',', ''))
                # list_count_dict[_list_name] = _list_rank / float(_num_books_on_list)     # TODO: switch this back to raw counts
                _list_name = _list.split()[:-2][0]
                _list_count = int(_list.split()[-2].replace(',', ''))
                list_count_dict[_list_name] = _list_count

        return list_count_dict


    def get_shelves(self, soup):

        shelf_count_dict = {}
        
        if soup.find('a', text='See top shelves…'):

            # Find shelves text.
            shelves_url = soup.find('a', text='See top shelves…')['href']
            source = urlopen('https://www.goodreads.com' + shelves_url)
            soup = bs4.BeautifulSoup(source, 'lxml')
            shelves = [' '.join(node.text.strip().split()) for node in soup.find_all('div', {'class': 'shelfStat'})]
            
            # Format shelves text.
            shelf_count_dict = {}
            for _shelf in shelves:
                _shelf_name = _shelf.split()[:-2][0]
                _shelf_count = int(_shelf.split()[-2].replace(',', ''))
                shelf_count_dict[_shelf_name] = _shelf_count

        return shelf_count_dict


    def get_genres(self, soup):
        genres = []
        for node in soup.find_all('div', {'class': 'left'}):
            current_genres = node.find_all('a', {'class': 'actionLinkLite bookPageGenreLink'})
            current_genre = ' > '.join([g.text for g in current_genres])
            if current_genre.strip():
                genres.append(current_genre)
        return genres


    def get_series_name(self, soup):
        series = soup.find(id="bookSeries").find("a")
        if series:
            series_name = re.search(r'\((.*?)\)', series.text).group(1)
            return series_name
        else:
            return ""


    def get_series_uri(self, soup):
        series = soup.find(id="bookSeries").find("a")
        if series:
            series_uri = series.get("href")
            return series_uri
        else:
            return ""

    def get_top_5_other_editions(self, soup):
        other_editions = []
        for div in soup.findAll('div', {'class': 'otherEdition'}):
            other_editions.append(div.find('a')['href'])
        return other_editions

    def get_isbn(self, soup):
        try:
            isbn = re.findall(r'nisbn: [0-9]{10}' , str(self, soup))[0].split()[1]
            return isbn
        except:
            return "isbn not found"

    def get_isbn13(self, soup):
        try:
            isbn13 = re.findall(r'nisbn13: [0-9]{13}' , str(self, soup))[0].split()[1]
            return isbn13
        except:
            return "isbn13 not found"


    def get_rating_distribution(self, soup):
        distribution = re.findall(r'renderRatingGraph\([\s]*\[[0-9,\s]+', str(self, soup))[0]
        distribution = ' '.join(distribution.split())
        distribution = [int(c.strip()) for c in distribution.split('[')[1].split(',')]
        distribution_dict = {'5 Stars': distribution[0],
                            '4 Stars': distribution[1],
                            '3 Stars': distribution[2],
                            '2 Stars': distribution[3],
                            '1 Star':  distribution[4]}
        return distribution_dict


    def get_num_pages(self, soup):
        if soup.find('span', {'itemprop': 'numberOfPages'}):
            num_pages = soup.find('span', {'itemprop': 'numberOfPages'}).text.strip()
            return int(num_pages.split()[0])
        return ''


    def get_year_first_published(self, soup):
        year_first_published = soup.find('nobr', attrs={'class':'greyText'})
        if year_first_published:
            year_first_published = year_first_published.string
            return re.search('([0-9]{3,4})', year_first_published).group(1)
        else:
            return ''

    def get_id(self, bookid):
        pattern = re.compile("([^.-]+)")
        return pattern.search(bookid).group()

    def get_my_rating(self, bookid):
        df = pd.read_csv(self.data_dir_read, sep='|')
        df = df[df['num_title'] == bookid]
        return df['my_rating'].item()
    
    def get_date_finished(self, bookid):
        df = pd.read_csv(self.data_dir_read, sep='|')
        df = df[df['num_title'] == bookid]
        return df['date_finished'].item()
    
    def get_cover_image(self, soup):
        series = soup.find('img', id='coverImage')
        if series:
            series_uri = series.get('src')
            return series_uri
        else:
            return ""
    
    def scrape_book(self, book_id):
        url = 'https://www.goodreads.com/book/show/' + book_id
        source = urlopen(url)
        soup = bs4.BeautifulSoup(source, 'html.parser')

        time.sleep(2)

        return {'book_id_title':        book_id,
                'book_id':              self.get_id(book_id),
                'book_title':           ' '.join(soup.find('h1', {'id': 'bookTitle'}).text.split()),
                # "book_series":          self.get_series_name(soup),
                # "book_series_uri":      self.get_series_uri(soup),
                # 'top_5_other_editions': self.get_top_5_other_editions(soup),
                # 'isbn':                 self.get_isbn(soup),
                # 'isbn13':               self.get_isbn13(soup),
                # 'year_first_published': self.get_year_first_published(soup),
                # 'authorlink':           soup.find('a', {'class': 'authorName'})['href'],
                # 'author':               ' '.join(soup.find('span', {'itemprop': 'name'}).text.split()),
                'num_pages':            self.get_num_pages(soup),
                'genres':               self.get_genres(soup),
                # 'shelves':              self.get_shelves(soup),
                # 'lists':                self.get_all_lists(soup),
                # 'num_ratings':          soup.find('meta', {'itemprop': 'ratingCount'})['content'].strip(),
                # 'num_reviews':          soup.find('meta', {'itemprop': 'reviewCount'})['content'].strip(),
                # 'average_rating':       soup.find('span', {'itemprop': 'ratingValue'}).text.strip(),
                # 'rating_distribution':  get_rating_distribution(soup),
                'cover':                self.get_cover_image(soup),
                'my_rating':            self.get_my_rating(book_id),
                'date_finished':        self.get_date_finished(book_id)
                }

    def condense_books(self, books_directory_path):

        books = []
        
        # Look for all the files in the directory and if they contain "book-metadata," then load them all and condense them into a single file
        for file_name in os.listdir(books_directory_path):
            if file_name.endswith('.json') and not file_name.startswith('.') and file_name != "all_books.json" and "book-metadata" in file_name:
                _book = json.load(open(books_directory_path + '/' + file_name, 'r')) #, encoding='utf-8', errors='ignore'))
                books.append(_book)

        return books

    def create_book_list(self, user_id):
        url = 'https://www.goodreads.com/review/list/' + str(user_id) + '?per_page=40&sort=date_read&utf8=%E2%9C%93'
        print(url)
        source = urlopen(url)
        soup = bs4.BeautifulSoup(source, 'html.parser')
        # print(soup)
        time.sleep(2)

        # read table
        table = soup.find_all("table", {"id":"books"})
        df = pd.read_html(str(table))[0]
        df = df[['title','author','rating','rating.1','read','cover']]
        df.columns = ['title','author','avg_rating','my_rating','date_finished','cover',]
        df = df[df['date_finished'].str.contains('2022')==True]

        rating_map = {
            'did not like it': '1',
            'it was ok': '2',
            'rating liked it': '3',
            'really liked it': '4',
            'it was amazing': '5'
        }

        for key, value in rating_map.items():
            df['my_rating'] = df['my_rating'].str.replace(key, value)
        df['my_rating'] = df['my_rating'].str[-1:]

        df['title'] = df['title'].str[6:]
        df['author'] = df['author'].str[7:]
        df['author'] = df['author'].apply(lambda x : ' '.join(x.split(',')[::-1]).replace('*', '').strip())
        df['author'] = df['author'].str.replace('  ', ' ')

        df['avg_rating'] = df['avg_rating'].str[-4:]

        df['date_finished'] = df['date_finished'].str[-12:]

        # df['date_finished'] = pd.to_datetime(df['date_finished'], format=r'%b %d, %Y')

        # get href
        book_titles = df['title'].tolist()
        print(len(book_titles))
        book_titles[:] = [x.replace('  ', ' ') for x in book_titles]
        book_title_links = []
        for book in book_titles:
            try:
                book_title_link = soup.find('a', {'title': book}).attrs['href']
                book_title_links.append(book_title_link)
            except AttributeError as e:
                print(book, ' had an attribute error. skipping. #TODO: Fix', e)
                book_title_links.append('')

        df['num_title'] = book_title_links
        df['num_title'] = df['num_title'].str[11:]
        df.to_csv(self.data_dir_read, sep='|', index=False)
        df = df[df['num_title'].map(len) > 5]
        df['num_title'].to_csv(r'my_books.txt', header=None, index=None, mode='w')


    def get_top_5_books(self, strip=False):
        df_top_5 = self.df.sort_values(by='my_rating', ascending=False)
        df_top_5 = df_top_5.head(5)
        df_top_5 = df_top_5['book_title'].tolist()
        if strip:
            df_top_5[:] = [x.split(':')[0] for x in df_top_5]
        return df_top_5

    def get_number_of_books_read(self):
        return self.df.shape[0]

    def get_most_read_genres(self):
        l = self.df['genres'].to_list()
        newlist = [item for items in l for item in items]
        l = ''.join(newlist)
        l = l.replace('[', '')
        l = l.replace(']', ', ')
        l = l.replace(', ', ',')
        l = l [:-2]
        l = l [1:]
        l = l.split("','")

        data = Counter(l)
        ignore = ['Audiobook','Adult','Contemporary','Adult Fiction','Book Club','Literary Fiction']
        for word in list(data):
            if word in ignore:
                del data[word]
        top_5 = data.most_common(5)
        top_5_string = []
        for i in top_5:
            stringed = ': '.join(map(str, i))
            top_5_string.append(stringed)
        return top_5_string

    def get_pages_tured(self):
        num_pages = '{:0,.0f}'.format(self.df['num_pages'].sum())
        return num_pages
