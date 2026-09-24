# confluence-mirror
The Python script for creating a dump of Confluence Space

# What it does
The Python scripts makes a search through a specified Confluence Space and recursively downloads attachments and pages, replacing links to preserve their structure. In details, it works this way:

## Getting the main page
A Confluence page consists of a tree of pages, but the API doesn’t expose it, the hierarchy is stored somewhere in the Confluence Database. The best I could get is to get the page and its child. So the first thing we need to do is to get the first page from the space, and it is the top page of the tree.

## Getting the tree of pages
When the script gets the top (main) page, it starts getting recursively deeper, requesting page details and HTML body, storing them into a structure. The script also downloads attachments at this stage, but it doesn’t save HTMLs for now. The environment variable DEPTH specifies how deep the tree should descend. The environment variable EXCLUSIONS_LIST (the default is "euit,notes,draft,handover") skips pages with these words in the title.

## Saving HTMLs
When the tree is built, it is time to save it to a filesystem. Before saving them, all pages are modified. Every page is parsed to replace links, from the Confluence links to the links of the pages that are now stored in files, relative to the backup website. The attachments and the page links are replaced. Because it can be done only when the whole tree is built, we can’t write pages into the filesystem before. This aspect affects the amount of memory needed for the Python script, all the content of the pages is stored in memory until the end.

# What to do with that
It is not a proper backup to be restored, use the official tools for that. I built it to make a simple mirror of Confluence. This backup is used to uploaded into an S3 bucket and setup a Cloudfront and work as a static web-site with the backup. It doesn't have all cool Atlassian visuals, table of content, etc. Use the tree at the end of each page for navigation or relative links.

# Getting Atlassian credentials for the script
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create a new User Token

# Envs
| Name | Description | Example |
|------|-------|-------|
| CONFLUENCE_URL | The URL to your Confluence | https://wiki.mysite.com |
| SPACE_KEY | The Space name | Development |
| USER_EMAIL | Access credentials | john.doe@mysite.com |
| USER_TOKEN | Access credentials | 1234567890 |
| DEPTH | The depth of the tree from the main space page | 10 |
| FAVICON_URL | Used for adding into all the pages HTML | https://wiki.mysite.com/favicon-update.ico |
| EXCLUSIONS_LIST | Comma-separated list of pages to exclude | euit,notes,draft,handover |
