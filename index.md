---
# recruiting banner on the home page: true = show, false = hide
recruiting: true
---

{% include section.html size="full" dark=true %}

{% assign member_count = 0 %}{% for m in site.members %}{% unless m.role contains "alumni" %}{% assign member_count = member_count | plus: 1 %}{% endunless %}{% endfor %}

<div class="hero" style="--hero: url('{{ "images/ajou1.jpg" | relative_url }}')">
  <p class="hero-eyebrow">Department of Biomedical Informatics · Ajou University School of Medicine</p>
  <h1 class="hero-title">Turning health data into <span>actionable evidence</span></h1>
  <p class="hero-text">
    The Ajou Health Data Science Lab bridges large-scale healthcare data and real-world evidence
    to improve patient outcomes and healthcare systems.
  </p>
  <div class="hero-actions">
    <a class="hero-primary" href="{{ "research" | relative_url }}">Explore our research <i class="fa-solid fa-arrow-right"></i></a>
    <a class="hero-secondary" href="{{ "contact" | relative_url }}">Join the lab</a>
  </div>
  <div class="hero-stats">
    <div class="hero-stat"><strong>{{ site.data.citations.size }}+</strong><span>Publications</span></div>
    <div class="hero-stat"><strong>{{ site.data.projects.size }}</strong><span>Research projects</span></div>
    <div class="hero-stat"><strong>{{ member_count }}</strong><span>Lab members</span></div>
  </div>
</div>

{% if page.recruiting %}
{% include section.html %}

<div class="cta">
  <div>
    <h2>We're recruiting</h2>
    <p>Open positions for MS / PhD / integrated MS-PhD students and research instructors (NLP, LLM, AI agents preferred).</p>
  </div>
  <a href="{{ "contact" | relative_url }}">See open positions <i class="fa-solid fa-arrow-right"></i></a>
</div>
{% endif %}

{% include section.html %}

<p class="section-eyebrow">What we do</p>

## Research areas

<div class="areas">
  <div class="area">
    <span class="area-icon"><i class="fa-solid fa-earth-asia"></i></span>
    <h3>Real-world evidence</h3>
    <p>Reliable evidence from large-scale, multi-center epidemiological studies using the OMOP Common Data Model.</p>
  </div>
  <div class="area">
    <span class="area-icon"><i class="fa-solid fa-brain"></i></span>
    <h3>Clinical AI</h3>
    <p>Clinical prediction models built with cutting-edge methods, including LLMs, foundation models, and agentic AI.</p>
  </div>
  <div class="area">
    <span class="area-icon"><i class="fa-solid fa-database"></i></span>
    <h3>Health data infrastructure</h3>
    <p>Data standardization, harmonization, and curation for reproducible medical research.</p>
  </div>
</div>

{% include section.html %}

<div class="section-head">
  <div>
    <p class="section-eyebrow">Latest</p>
    <h2>News</h2>
  </div>
  {% include button.html link="blog" text="All news" icon="fa-solid fa-arrow-right" flip=true style="bare" %}
</div>

<div class="news">
{% for post in site.posts limit: 3 %}
  <a class="news-card" href="{{ post.url | relative_url }}">
    {% if post.image %}<img src="{{ post.image | relative_url }}" alt="" loading="lazy">{% endif %}
    <div>
      <span class="news-date">{{ post.date | date: "%b %-d, %Y" }}</span>
      <span class="news-title">{{ post.title }}</span>
    </div>
  </a>
{% endfor %}
</div>

{% include section.html %}

<div class="section-head">
  <div>
    <p class="section-eyebrow">Selected</p>
    <h2>Publications</h2>
  </div>
  {% include button.html link="research" text="All publications" icon="fa-solid fa-arrow-right" flip=true style="bare" %}
</div>

{% include citation.html lookup="Real-world evidence for comparative safety of second-line antihyperglycemic agents in older adults with type 2 diabetes" style="rich" %}

{% include citation.html lookup="Uptake of and Disparities in Semaglutide and Tirzepatide Prescribing for Obesity in the US" style="rich" %}
