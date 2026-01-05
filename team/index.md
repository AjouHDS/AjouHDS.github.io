---
title: Team
nav:
  order: 1
  tooltip: About Ajou Health Data Science Lab team
---

# {% include icon.html icon="fa-solid fa-users" %}Team

Introducing the team members of the Ajou Health Data Sciences Lab. We strive for both career growth and personal growth in our lab.

{% include section.html %}

## Current members
{% include list.html data="members" component="portrait" filter="role == 'pi'" %} 

{% include list.html data="members" component="portrait" filter="role == 'postdoc'" %}

{% include list.html data="members" component="portrait" filter="role == 'phd'" %}

## Alumni
{% include list.html data="members" component="portrait" filter="role == 'alumni'" %} 

{% include section.html %}

## Collaborators

<div style="display: flex; align-items: center; justify-content: center; gap: 20px; row-gap: 10px; flex-wrap: wrap;">

{% include figure.html image="images/ajou_hospital.png" link="https://hosp.ajoumc.or.kr/" height="100px" %}
{% include figure.html image="images/ohdsi.png" link="https://www.ohdsi.org/" height="100px" %}
{% include figure.html image="images/yale_med.png" link="https://medicine.yale.edu/" height="100px" %}
{% include figure.html image="images/ynhh_core.png" link="https://medicine.yale.edu/core/" height="100px" %}
{% include figure.html image="images/yonsei.png" link="https://www.yonsei.ac.kr/" height="100px" %}
{% include figure.html image="images/bongdam.png" link="http://bdforestmind.com/" height="100px" %}

</div>

{% include section.html %}

{% capture content %}

{% include figure.html image="images/ajou1.png" %}
{% include figure.html image="images/ajou2.png" %}
{% include figure.html image="images/ajou4.png" %}

{% endcapture %}

{% include grid.html style="square" content=content %}
