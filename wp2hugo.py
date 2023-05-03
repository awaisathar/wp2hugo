import sys
import wpparser
import argparse
import pathlib
import os
from markdownify import MarkdownConverter
import urllib.request
import urllib.parse
import html

class ImageBlockConverter(MarkdownConverter):
    def __init__(self, **options):
        super().__init__(**options)
        self.cover_image = None

    def convert_img(self, el, text, convert_as_inline):        
        url = el.attrs['src']
        if url.startswith(self.options['blog_url']) or url.startswith(self.options['blog_url'].replace('https', 'http')):
            self.download_resource(url)
            el.attrs['src'] = url.split('/')[-1]
            # treat first image as cover
            if not self.cover_image: self.cover_image = el.attrs['src']
        return super().convert_img(el, text, convert_as_inline)

    def convert_a(self, el, text, convert_as_inline):
        url = el.attrs['href']
        if url.startswith(self.options['blog_url']) or url.startswith(self.options['blog_url'].replace('https', 'http')):
            self.download_resource(url)
            el.attrs['href'] = url.split('/')[-1]       
        return super().convert_a(el, text, convert_as_inline)
    
    def download_resource(self, url):
        filename = url.split('/')[-1]
        resource = self.options['page'] + filename
        if not os.path.exists(resource): 
            try:
                print(f"Saving {self.options['page']}{filename}")
                urllib.request.urlretrieve(url, resource)
            except:
                print(f"{url} could not be downloaded", file=sys.stderr)

class WP2Hugo:
    def __init__(self, xml, out):
        self.output_folder = out
        self.data = wpparser.parse(xml)
        self.blog_url = self.data['blog']['blog_url']

    def convert(self):    
        for post in self.data['posts']:
            post['post_name'] = urllib.parse.unquote(post['post_name'])
            page =  f"{self.output_folder}/content/posts/{post['post_name']}" 
            pathlib.Path(page).mkdir(parents=True, exist_ok=True)
            markdown = self.post_to_markdown(post)
            print(f"Creating page {page}")
            with open( f"{page}/index.md", 'w', encoding="utf-8") as f:
                f.writelines(markdown)

    def format_markdown(self,text):
        return html.unescape(text).replace("'","''")

    def post_to_markdown(self, post):
        post_name = post['post_name']
        page = f"{self.output_folder}/content/posts/{post_name}/" 
        title = self.format_markdown(post['title']) 
        tags = list(map( lambda c: self.format_markdown(c), post['categories']))
        converter = ImageBlockConverter(blog_url=self.blog_url, page = page)
        content = converter.convert(post['content'])

        # get cover, if present
        cover_section = f"cover:\n   image: {converter.cover_image}\n" if converter.cover_image else ''
        

        
        # get image list
        resource_list = '\n'.join([f"   - src: {f.name}" for f in os.scandir(page) if f.name != 'index.md' ])

        return f"""---
id: {post['post_id']}
title: '{title}'
url: {post_name}
date: { post['post_date_gmt'] }
draft: false
tags: {tags}
{cover_section}resources:
{resource_list}
---
{content}"""
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("xml", help="Wordpress Exported XML")
    parser.add_argument("out", help="Hugo site root folder. Pages are placed in <out>/content/posts")
    args = parser.parse_args()
    wp2hugo = WP2Hugo(args.xml, args.out)
    wp2hugo.convert()
