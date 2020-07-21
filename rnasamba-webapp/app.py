import os
import uuid

import pandas as pd
from Bio import SeqIO
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename
from worker import celery


# Define global variables
TITLE = 'RNAsamba: coding potential calculator for transcript sequences'
BASE_PATH = '/rnasamba-app'
UPLOAD_FOLDER = os.path.join(BASE_PATH, 'uploads')
ALLOWED_EXTENSIONS = ['fasta', 'fa', 'fna']

# Disable pandas max_colwidth
pd.set_option('display.max_colwidth', -1)

# Create Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        model = 'full_length_weights.hdf5'
        # Check input file extension
        input_file = request.files['file']
        if not allowed_file(input_file.filename):
            flash('Only FASTA, FA and FNA files are allowed.', 'danger')
            return redirect(request.url)
        if input_file and allowed_file(input_file.filename):
            filename = secure_filename(input_file.filename)
            # Add 5 random characters to the file name and save it to the uploads directory
            filename = '{}_{}{}'.format(
                os.path.splitext(filename)[0],
                uuid.uuid4().hex[0:5],
                os.path.splitext(filename)[1],
            )
            input_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            input_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Check if the file is in the FASTA format
            if not is_fasta(input_file_path):
                flash(
                    'The file you uploaded was not recognized as a FASTA file.', 'danger'
                )
                return redirect(request.url)
            # Check the number of sequences in the FASTA file
            n_seq = 0
            with open(input_file_path) as input:
                for line in input:
                    if line.startswith('>'):
                        n_seq += 1
            if n_seq > 50000:
                flash('The uploaded file contains more than 50,000 sequences.', 'danger')
                return redirect(request.url)
            # Create a name for the output
            output_file = '{}_{}.tsv'.format(os.path.splitext(filename)[0], 'rnasamba')
            output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], output_file)
            # Start a Celery task and send user to the results page
            celery.send_task(
                'tasks.start_rnasamba',
                args=[input_file_path, output_file_path, model],
                kwargs={},
            )
            return submission_complete(output_file)
    return render_template('index.html', title=TITLE)


@app.route('/')
def submission_complete(output_file):
    output_file_base = os.path.splitext(output_file)[0]
    download_url = request.base_url + output_file_base
    return render_template('submission.html', download_url=download_url, title=TITLE)


@app.route('/<output_file_base>')
def results_page(output_file_base):
    output_file = output_file_base + '.tsv'
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], output_file)
    if os.path.exists(output_file_path):
        dataframe = pd.read_csv(output_file_path, sep='\t', index_col=None)
        data_size = dataframe.shape[0]
        dataframe.columns = ['Sequence ID', 'Coding probability', 'Classification']
        dataframe_html = dataframe.to_html(
            index=False,
            justify='left',
            table_id='dataframe-id',
            border=0,
            classes=['table', 'table-striped', 'table-hover', 'nowrap'],
        )
        return render_template(
            'results.html',
            output_file=output_file,
            data_size=data_size,
            dataframe_html=dataframe_html,
            title=TITLE,
        )
    else:
        return render_template('missing.html', title=TITLE)


@app.route('/uploads/<output_file>')
def uploaded_file(output_file):
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], output_file)
    if os.path.exists(output_file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], output_file)
    else:
        return render_template('missing.html', title=TITLE)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_fasta(file):
    with open(file, 'r') as handle:
        fasta = SeqIO.parse(handle, 'fasta')
        return any(fasta)


if __name__ == '__main__':
    app.run(debug=False)
