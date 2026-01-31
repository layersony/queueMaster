
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from jobs.models import Job, JobStatus

st.title("Job Queue Monitoring")

# Real-time stats
response = requests.get("http://api:8000/api/v1/jobs/stats/")
stats = response.json()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Queued", stats['redis']['queued'])
col2.metric("Processing", stats['redis']['processing'])
col3.metric("Scheduled", stats['redis']['scheduled'])
col4.metric("Dead Letter", stats['redis']['dead_letter'])

# Recent failed jobs
st.subheader("Recent Failures")
failed_jobs = Job.objects.filter(
    status=JobStatus.FAILED,
    updated_at__gte=datetime.now() - timedelta(hours=24)
).order_by('-updated_at')[:10]

st.dataframe(failed_jobs.values('id', 'task_type', 'error_message', 'retry_count'))