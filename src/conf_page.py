import os
import string
import urllib.request
import requests
from jinja2 import Environment, FileSystemLoader
from atlassian import Confluence
from pathlib import Path
from datetime import datetime
from lxml import html
from loguru import logger


# Represents a Confluence page in tree structure:
# id=[1111] title=[Overview] childs_count=[3]
#     id=[1112] title=[Sample Pages] childs_count=[3]
#         id=[1113] title=[Meeting notes] childs_count=[0]
#         id=[1114] title=[Decision] childs_count=[0]
#         id=[1115] title=[Product requirements] childs_count=[0]
#     id=[1116] title=[Confluence Recap] childs_count=[0]
#     id=[1117] title=[Test page] childs_count=[0]
class Conf_page:
    title = ""
    title_slug = ""
    id = ""
    content = ""
    relative_path = ""
    local_base_path = ""
    html_file_suffix = ".html"
    attachments = {}
    attachments_folder_suffix = "-attachments"
    childs = []

    def __init__(
        self,
        title="",
        title_slug="",
        id="",
        content="",
        relative_path="",
        local_base_path="",
        html_file_suffix=".html",
        attachments={},
        childs=[],
    ):
        self.title = title
        self.title_slug = title_slug
        self.id = id
        self.content = content
        self.relative_path = relative_path
        self.local_base_path = local_base_path
        self.html_file_suffix = html_file_suffix
        self.attachments = attachments
        self.childs = childs

    def _build_hierarchy(self, indent: int = 0, indent_inc: int = 4) -> list:
        result = []
        result.append(
            f"{' ' * indent}id=[{self.id}] title=[{self.title}] childs_count=[{len(self.childs)}] relative_path=[{self.relative_path}] local_base_path=[{self.local_base_path}] with HTML content=[{'Yes' if len(self.content) > 0 else 'No'}]"
        )
        for child in self.childs:
            result.extend(
                child._build_hierarchy(
                    indent=indent + indent_inc, indent_inc=indent_inc
                )
            )
        return result

    def __len__(self):
        return len(self.childs)

    def __repr__(self):
        return str({"id": self.id, "title": self.title, "childs": self.childs})

    def __str__(self):
        return "\n".join(self._build_hierarchy())


class Conf_API:
    confluence_url = ""  # Confluence base URL
    space = ""  # Confluence SPACE
    pages = None
    confluence = None
    jira = None
    users = {}
    pages_created_count = 0
    pages_requested_count = 0
    logger = None
    script_dirname = ""

    # The flat dict of all pages in the space and their location. Needs for building A-links between pages
    # {
    #     "123123": "Overview.html",
    #     "1242424": "Overview/Sample Pages.html",
    #     "122321323": "Overview/Test page.html"
    # }
    pages_list = {}

    def __init__(self, confluence_url, username, api_token, logger=None):
        self.logger = logger
        self.script_dirname = os.path.dirname(__file__)
        self.confluence_url = confluence_url
        session =  requests.Session()
        self.confluence = Confluence(
            url=confluence_url, username=username, password=api_token, session=session,
        )
        self.pages = Conf_page()

    # Downloads all pages in a Confluence SPACE to a specified path
    def download_space(
        self, space: str = None, path: str = None, limit: int = 50, max_depth: int = 100, exclusions_list: list = [], favicon_url: str = None
    ) -> None:
        now = datetime.now()
        self.logger.warning(f"Starting download for space: {space}")
        self.space = space
        if not path:
            path = "."
        if favicon_url:
            self.download_file(
                url=favicon_url,
                dest_path=str(os.path.join(path, "favicon.ico")),
            )
        self.logger.warning(
            f"Downloading space: [{space}] to path: [{path}] with maximum depth={max_depth}"
        )
        pages = self.get_space_pages(
            space=space, limit=limit, max_depth=max_depth, path=path, exclusions_list=exclusions_list
        )
        self.pages = pages
        self.logger.info(f"The space tree: {self.pages}")
        self.logger.debug(
            "The pages list: "
            + ";".join([f"{page}: {path}" for page, path in self.pages_list.items()])
        )
        self.build_content_page(pages)
        self.build_pages(pages)
        self.build_index_page(
            space=space,
            pages_created_count=self.pages_created_count,
            date=now.strftime("%d-%m-%Y %H:%M:%S"),
            pages=pages,
            path=path,
        )
        self.logger.warning(
            f"Finished downloading space: [{space}] to path: [{path}] with total pages downloaded={self.pages_created_count}"
        )

    def build_content_page(self, pages: Conf_page, path: str = "/tmp/conf_backup") -> None:
        filepath = os.path.join(path, "content.html")
        self.logger.info(
            f"Building content.html file at [{filepath}] where all the pages are listed"
        )
        tree = self.get_html_pages_list_v2(current_page=pages, collapsed=False)
        templates = Environment(loader=FileSystemLoader(os.path.join(self.script_dirname, "templates/")))
        content = templates.get_template("content.j2")
        html = content.render(
            title="Content table",
            content=tree
        )
        with open(filepath, mode="w", encoding="utf-8") as file:
            file.write(html)

    # Create index page because Confluence spacehas main page with custom name. This page will have table of contents of all downloaded pages
    def build_index_page(
        self,
        space: str,
        pages_created_count: int,
        date: str,
        pages: Conf_page,
        path: str = "/tmp/conf_backup",
    ) -> None:
        filepath = os.path.join(path, "index.html")
        self.logger.info(
            f"Building page index.html page with a table of contents at [{filepath}]"
        )
        templates = Environment(loader=FileSystemLoader(os.path.join(self.script_dirname, "templates/")))
        index = templates.get_template("index.j2")
        html = index.render(
            title="Backup contents",
            space=space,
            pages_created_count=pages_created_count,
            date=date,
            tree='<iframe src="content.html" width="100%" height="1000" frameborder="0"></iframe>' # tree=self.get_html_pages_list_v2(current_page=pages, collapsed=False),
        )
        with open(filepath, mode="w", encoding="utf-8") as file:
            file.write(html)

    # Returns all the pages of a Confluence SPACE as a tree structure
    def get_space_pages(
        self,
        space: str = "MYSPACE",
        limit: int = 50,
        max_depth=100,
        path: str = "/tmp/conf_backup",
        exclusions_list: list = []
    ) -> Conf_page:
        self.logger.warning(
            f"Fetching pages for space: {space} with  maximum depth={max_depth}"
        )
        main_page_id = self.get_main_page_id(space)
        pages = self.get_pages_from_parent(
            parent=main_page_id,
            limit=limit,
            max_depth=max_depth,
            path=path,
            get_attachments=True,
            exclusions_list=exclusions_list,
        )
        return pages

    # Gets the main page ID of a Confluence SPACE, it is needed because all the pages are organized in a tree structure under the main page
    def get_main_page_id(self, space: str = "MYSPACE") -> str:
        main_page = self.confluence.get_space_content(
            space, depth="1", start=0, limit=1, content_type="page", expand=None
        )
        self.pages_list.update(
            {space: "/" + main_page["results"][0]["title"] + ".html"}
        )  # adding the top page of the Space
        return main_page["results"][0]["id"]

    # Returns all the pages under a specific parent page as a tree structure
    def get_pages_from_parent(
        self,
        parent: str,
        limit: int = 50,
        max_depth=100,
        path: str = "",
        get_attachments=True,
        exclusions_list: list = [],
    ) -> Conf_page:
        self.logger.warning(
            f"Fetching pages for parent: {parent} with maximum depth={max_depth}"
        )
        self.pages = self.get_childs_v2(
            parent,
            limit=limit,
            max_depth=max_depth,
            current_depth=1,
            relative_path="",
            local_base_path=path,
            get_attachments=get_attachments,
            exclusions_list=exclusions_list,
        )
        self.logger.info(f"Finished fetching pages for parent: {parent}")
        return self.pages

    # Returns a Conf_page object by the page ID
    def get_page_by_id(self, page_id: str) -> Conf_page:
        self.logger.debug(f"Getting the page HTML by ID [{page_id}]")
        page = self.confluence.get_page_by_id(page_id, expand="body.view")
        self.pages_requested_count += 1
        if self.pages_requested_count % 50 == 0:
            self.logger.debug(f"Total pages requested so far: {self.pages_requested_count}")
        conf_page = Conf_page(
            title=page["title"],
            title_slug=self.cleanup_title(page["title"]),
            id=page["id"],
            childs=[],
            content=page["body"]["view"]["value"],
        )
        self.pages_created_count += 1
        return conf_page

    # Cleans up the title to make it URL-safe, removes spaces, non-printable characters, emojis, etc
    def cleanup_title(self, title: str) -> str:
        return ''.join([c for c in title if c in string.printable])

    # Saves all attachments from a page by its ID to a specified path
    def get_page_attachments_v2(self, page: Conf_page) -> dict:
        result = {}
        self.logger.debug(f"Fetching attachments for page ID [{page.id}]")
        path = Path(
            page.local_base_path, page.relative_path + page.attachments_folder_suffix
        )
        try:
            path.mkdir(parents=True, exist_ok=True)
            attachments = self.confluence.download_attachments_from_page(
                page.id, path=path
            )
            if (
                isinstance(attachments, str)
                and attachments == "No attachments found on the page."
            ):
                self.logger.debug(f"No attachments found")
                path.rmdir()
            elif isinstance(attachments, dict):
                self.logger.info(
                    f"{str(attachments["attachments_downloaded"])} attachments downloaded for page [{page.id}]"
                )
                result = {
                    file.name: str(file).removeprefix(page.local_base_path)
                    for file in list(path.glob("*"))
                }
                # self.logger.debug(f"Attachments downloaded: {json.dumps(result)}")
                if len(result) != attachments["attachments_downloaded"]:
                    self.logger.critical(
                        f"The number of downloaded attachments [{len(result)}] does not match the expected count [{attachments['attachments_downloaded']}]!"
                    )
        except Exception as e:
            self.logger.error("Error while downloading attachments: " + str(e))
        return result

    # Returns a list of child pages for a given page ID
    def get_childs_v2(
        self,
        page_id: str,
        start: int = 0,
        limit: int = 50,
        relative_path: str = "",
        local_base_path: str = "",
        max_depth: int = 10,
        current_depth: int = 1,
        get_attachments=True,
        exclusions_list: list = []
    ) -> Conf_page:
        self.logger.debug(
            f"Getting the page and its childs by ID [{page_id}] current_depth=[{current_depth}], max_depth=[{max_depth}]"
        )
        page = self.get_page_by_id(page_id)
        page.relative_path = os.path.join(relative_path, page.title_slug)
        page.local_base_path = local_base_path
        self.pages_list.update(
            {page.id: "/" + page.relative_path + page.html_file_suffix}
        )
        if get_attachments:
            page.attachments = self.get_page_attachments_v2(page)
        if current_depth < max_depth:
            self.logger.debug(
                f"Fetching child pages for page ID [{page_id}] start=[{start}], limit=[{limit}], current_depth=[{current_depth}], max_depth=[{max_depth}]"
            )
            childs_tmp = self.get_all_childs(page_id, start=start, limit=limit, exclusions_list=exclusions_list)
            self.logger.debug(f"Childs for [{page_id}] found = {len(childs_tmp)}")
            for child in childs_tmp:
                page.childs.append(
                    self.get_childs_v2(
                        child["id"],
                        start=start,
                        limit=limit,
                        max_depth=max_depth,
                        current_depth=current_depth + 1,
                        relative_path=page.relative_path,
                        local_base_path=page.local_base_path,
                        get_attachments=get_attachments,
                        exclusions_list=exclusions_list,
                    )
                )
        else:
            self.logger.debug(
                f"Maximum depth [{max_depth}] reached at page ID [{page.id}]: {page.title}"
            )
        return page

    # Recursively returns all child pages
    def get_all_childs(self, page_id: str, start: int = 0, limit: int = 50, exclusions_list: list = []) -> list:
        self.logger.debug(f"Paginate [{page_id}], start=[{start}], limit=[{limit}]")
        childs_tmp = self.confluence.get_page_child_by_type(
            page_id, type="page", start=start, limit=limit, expand=None
        )  # get a list of childs
        if len(childs_tmp) == limit:
            self.logger.debug(
                f"More pages available, fetching next batch starting from [{start + limit}]"
            )
            childs_tmp.extend(
                self.get_all_childs(page_id, start=start + limit, limit=limit, exclusions_list=exclusions_list)
            )
        return self.filter_out_pages(
            childs_tmp, titles_to_exclude=exclusions_list
        )

    # Filters out pages based on titles to exclude, using EXCLUSIONS_LIST env
    def filter_out_pages(self, pages: list, titles_to_exclude: list) -> list:
        result = []
        for page in pages:
            valid = True
            for exclusion in titles_to_exclude:
                if exclusion.lower() in page["title"].lower():
                    self.logger.warning(
                        f"Excluding page [{page['title']}] with ID [{page['id']}] as per the exclusion list, exclusion: [{exclusion}]"
                    )
                    valid = False
                    break
            if valid is True:
                result.append(page)
        return result

    # Recursively builds and saves all pages
    def build_pages(self, pages: Conf_page) -> None:
        self.build_page(pages)
        for child in pages.childs:
            self.build_pages(child)

    # Build page, repliacing links and saving to a file
    def build_page(self, pages: Conf_page) -> None:
        self.logger.info(
            f"Building page [{pages.title}] with ID [{pages.id}] at [{os.path.join(pages.local_base_path, pages.relative_path + pages.html_file_suffix)}]"
        )
        templates = Environment(loader=FileSystemLoader(os.path.join(self.script_dirname, "templates/")))
        page_built = templates.get_template("page.j2")
        # tree = self.get_html_pages_list_v2(current_page=pages, collapsed=True)

        rewritten_content = self.replacing_links(
            space=self.space,
            html_content=pages.content,
            pages_list=self.pages_list,
            attachments=pages.attachments,
        )
        html = page_built.render(
            title=pages.title, content=rewritten_content, tree='<iframe src="/content.html" width="100%" height="1000" frameborder="0"></iframe>'
        )
        filepath = os.path.join(
            pages.local_base_path, pages.relative_path + pages.html_file_suffix
        )
        with open(filepath, mode="w", encoding="utf-8") as file:
            self.logger.debug(f"Writing templated [{pages.title}] to [{filepath}]")
            file.write(html)

    # Replacing A-links and attachment links to local files
    def replacing_links(
        self, space: str, html_content: str, pages_list: dict, attachments: dict = {}
    ) -> str:
        if html_content.strip() == "":
            return ""
        body = html.fromstring(html_content)
        # replacing a-links into local links
        try:
            for element in body.xpath("//a[@href]"):
                href = element.get("href")
                self.logger.debug("HREF " + href)
                if href.strip() == "#" or href.strip() == "":
                    self.logger.debug("Skipping empty link")
                    continue  # skipping empty links
                if ("/wiki/people/" in href) or ("mailto" in href):
                    self.logger.debug("Skipping user profile link")
                    continue  # skipping user profile links TBD
                if href == "/wiki/spaces/" + space or href.split("/")[-2] == space:
                    self.logger.debug("Found the Space main page link", href)
                    new_href = pages_list[space]
                    self.logger.debug(
                        f"Replacing link the Space main page link {pages_list[space]}"
                    )
                    element.set("href", new_href)
                elif f"/wiki/spaces/{space}/pages/" in href:
                    self.logger.debug("Found inspace link", href)
                    page_id = href.split("/")[-2]
                    if page_id in pages_list:
                        self.logger.debug(
                            f"Page {page_id} found in pages_list, replacing link"
                        )
                        new_href = pages_list[page_id]
                        self.logger.debug(
                            f"Replacing link for page ID: {page_id} to {new_href}"
                        )
                        element.set("href", new_href)
                elif href.startswith("/wiki/spaces/") and not href.startswith(
                    "/wiki/spaces/" + space
                ):
                    self.logger.debug(
                        f"Remaking link to another Space, setting absolute URL, from [{href}] to [{self.confluence_url + href}]"
                    )
                    element.set("href", self.confluence_url + href)
        except Exception as e:
            self.logger.error("Error while replacing links: " + str(e), exc_info=e)
        # replacing attachment linkgs into local files
        try:
            for element in body.xpath("//img[@data-linked-resource-default-alias]"):
                file_name = element.get("data-linked-resource-default-alias")
                self.logger.debug("PICTURE " + file_name)
                if file_name in attachments:
                    self.logger.debug(
                        "Found the image on the page from the attachment folder, replacing the link",
                        element.get("data-linked-resource-default-alias"),
                    )
                    new_href = attachments[file_name]
                    element.set("srcset", new_href)
                    element.set("src", new_href)
        except Exception as e:
            self.logger.error(
                "Error while replacing attachment links: " + str(e), exc_info=e
            )
        return html.tostring(body, encoding="unicode", method="html")

    # Recursively returns the tree of pages in HTML list
    def get_html_pages_list_v2(
        self, current_page: Conf_page = None, collapsed: bool = True
    ) -> str:
        if self.pages is not None:
            result = "<h2>Full backup structure:</h2>\n"
            if collapsed is True:
                result += "<details>\n"
            result += f'<li><a href="{self.pages_list.get(self.space)}" target="_top">{"<b>" if self.pages.id == current_page.id else ""}{self.pages.title}{"</b>" if self.pages.id == current_page.id else ""}</a></li>\n'
            if len(self.pages.childs) > 0:
                result += "<ul>\n"
                for child in self.pages.childs:
                    result += self._get_html_pages_list_recursive(
                        pages=child, current_page=current_page
                    )
                result += "</ul>\n"
            if collapsed is True:
                result += "</details>\n"
        else:
            result = "<h2>The backup is empty!</h2>"
        return result

    # Recursively returns all child pages as HTML list items
    def _get_html_pages_list_recursive(
        self, pages: Conf_page, current_page: Conf_page = None
    ) -> str:
        result = f'<li><a href="{self.pages_list.get(pages.id, self.pages_list.get(self.space, ""))}" target="_top">{"<b>" if pages.id == current_page.id else ""}{pages.title}{"</b>" if pages.id == current_page.id else ""}</a></li>\n'
        if len(pages.childs) > 0:
            result += "<ul>\n"
            for child in pages.childs:
                result += self._get_html_pages_list_recursive(
                    pages=child, current_page=current_page
                )
            result += "</ul>\n"
        return result

    # Downloads a file from a URL to a specified local path, used for favicon download
    def download_file(self, url: str, dest_path: str) -> None:
        self.logger.info(f"Downloading file from [{url}] to [{dest_path}]")
        Path(os.path.dirname(dest_path)).mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as response, open(dest_path, "wb") as out_file:
            out_file.write(response.read())
