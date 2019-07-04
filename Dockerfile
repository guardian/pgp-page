# ---- Base Python ----
FROM python:3.7
WORKDIR /secure-contact

# ---- Dependencies ---- 
COPY requirements.txt /secure-contact/requirements.txt
RUN pip install -r requirements.txt

# --- SRC and scripts ---
COPY static /secure-contact/static
COPY templates /secure-contact/templates
COPY pgp_listing.py /secure-contact/
COPY pgp_manager.py /secure-contact/

CMD python /secure-contact/pgp_listing.py