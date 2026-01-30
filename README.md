# CiteScan: Check References, Confirm Truth.

<!-- - **🎉 CiteScan is now available online. [https://huggingface.co/spaces/thinkwee/CiteScan](https://huggingface.co/spaces/thinkwee/CiteScan)!  🎉** -->


**CiteScan**  is an open-source and free tool designed to detect hallucinated references in academic writing. As AI coding assistants and writing tools become more prevalent, they sometimes generate plausible-sounding citations that do not actually exist. **CiteScan**  addresses this issue by validating every bibliography entry against multiple authoritative academic databases—including arXiv, CrossRef, DBLP, Semantic Scholar, OpenAlex, and Google Scholar—to confirm their authenticity.

Going beyond simple verification, **CiteScan** used rule-based algorithms to analyze whether the cited papers genuinely support the claims made in your text. Thanks to the free accessibility for academic databases across CS and AI areas, our system will **cost $0 for maintenance after development**. 


## 🛡 Why CiteScan?

-   **🚫 NO Hallucinations**: Annotate citations that don't exist or have mismatched metadata across year, authors, and title. 

-   **📋 Ground Truth Reference**: Provide the link if the citations are flagged to *issued entry*. You can click the **Open paper** or **DOI** button to access the real-world metadata, and Then cite the BibTex from the press website.
 
![Functions](assets/screenshot_performance_zh.png)

-   **🏠 Top-tier Research Organizations**: Cooperate with National University of Singapore (NUS) and Shanghai Jiao Tong University (SJTU). 

## References Validation
-   **Multi-Source Verification**: Validates metadata against arXiv, CrossRef, DBLP, Semantic Scholar, OpenAlex, and Google Scholar



![Citation](assets/screenshot_semantic_scholar.png)


### Understanding Mismatches

*False positive cases* occur for CiteScan:

1.  **Authors Mismatch**:
    - *Reason*: Different databases deal with a longer list of  authors with different strategies, like truncation.
    - *Action*: Verify if main authors match

2.  **Venues Mismatch**:
    - *Reason*: Abbreviations vs. full names, such as "ICLR" v.s. "International Conference on Learning Representations"
    - *Action*: Both are correct.

3.  **Year GAP (±1 Year)**:
    - *Reason*: Delay between preprint (arXiv) and final version publication 
    - *Action*: Verify which version you intend to cite, We recommend you to cite the version from the official press website. Lower pre-print version bib will make your submission more confidence. 

4.  **Non-academic Sources**:
    - *Reason*: Blogs, and APIs are not indexed in academic databases.
    - *Action*: Verify URL, year, and title manually.


## 🙏 Acknowledgments

CiteScan uses multiple data sources:
- arXiv API
- CrossRef API
- Semantic Scholar API
- DBLP API
- OpenAlex API


### Push
```shell

# 如果已经添加过 modelscope 远程，先删掉再加：
git remote remove modelscope
git remote add modelscope "http://oauth2:ms-28735aa7-04b6-4b21-b4e0-cfb464f3587f@www.modelscope.cn/studios/aivolcano/CiteScan.git"

# 添加 ModelScope 为远程仓库
git remote add modelscope "http://oauth2:ms-28735aa7-04b6-4b21-b4e0-cfb464f3587f@www.modelscope.cn/studios/aivolcano/CiteScan.git"

# 推送到创空间(主分支是 main 时)
git push modelscope main

# 推送到创空间(主分支是 master 时)
git push modelscope master


# 若推送时报错
git push modelscope main --force

# 推送成功后
https://www.modelscope.cn/studios/aivolcano/CiteScan
# 创空间里点 「上线空间展示」 或 「立即发布」，等部署完成即可访问 Gradio 应用。
```

