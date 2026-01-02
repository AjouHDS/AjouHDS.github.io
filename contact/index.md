---
title: Contact
nav:
  order: 5
  tooltip: Email, address, and location
---

# {% include icon.html icon="fa-regular fa-envelope" %}Contact

We are actively recruiting new members! If you are interested, please send your CV to us.

{%
  include button.html
  type="email"
  text="ted9219@gmail.com"
  link="ted9219@gmail.com"
%}
{%
  include button.html
  type="phone"
  text="(031) 219-4471"
  link="+82-31-219-4471"
%}
{%
  include button.html
  type="address"
  tooltip="Our location on Google Maps for easy navigation"
  link="https://maps.app.goo.gl/qCzjSdrbnyUFPppL8"
%}

{% include section.html %}

{% capture col1 %}

{%
  include figure.html
  image="images/ajou1.png"
  caption="Ajou University Medical Center"
%}

{% endcapture %}

{% capture col2 %}

{%
  include figure.html
  image="images/ajou4.png"
  caption="Innovative Medical R&D Building (Lab located)"
%}

{% endcapture %}

{% include cols.html col1=col1 col2=col2 %}

{% include section.html dark=true %}

{% capture col1 %}
Lorem ipsum dolor sit amet  
consectetur adipiscing elit  
sed do eiusmod tempor
{% endcapture %}

{% capture col2 %}
Lorem ipsum dolor sit amet  
consectetur adipiscing elit  
sed do eiusmod tempor
{% endcapture %}

{% capture col3 %}
Lorem ipsum dolor sit amet  
consectetur adipiscing elit  
sed do eiusmod tempor
{% endcapture %}

{% include cols.html col1=col1 col2=col2 col3=col3 %}
