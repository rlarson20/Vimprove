if __name__ == "__main__":
    with open("./sample-readme.md") as f:
        chunks = chunk_markdown(f.read(), "telescope.nvim")
        __import__("pprint").pprint(chunks)
