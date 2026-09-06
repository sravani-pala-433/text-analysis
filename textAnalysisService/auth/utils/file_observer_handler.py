import os
import shutil
import threading
from plistlib import InvalidFileException
from queue import Queue
import asyncio
import numpy as np
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging
from textAnalysisService.auth.config import config
from textAnalysisService.auth.schema import TextContentRow, TextEmbeddingRow, TextEmbeddingRowV1
from textAnalysisService.auth.services.textset_service import TextSetService
from textAnalysisService.auth.utils.util_func import parse_iso8601_date, check_and_replace_nan, \
    extract_request_details_from_file_path
from tokenizer.embedings import handle_embeddings_list

logger = logging.getLogger(__name__)

textset_service = TextSetService()


class FileObserverHandler(FileSystemEventHandler):
    """Handles file system events."""

    def __init__(self, queue: Queue, success_dir: str, failed_dir: str):
        self.queue = queue
        self.success_dir = success_dir
        self.failed_dir = failed_dir

    def on_created(self, event):
        if not event.is_directory:
            self.queue.put(event.src_path)  # Put the file path into the queue for processing

    def on_modified(self, event):
        if not event.is_directory:
            self.queue.put(event.src_path)  # Put the file path into the queue for processing

    def process_file(self, file_path):
        """Reads the content of the observed file and processes it."""
        try:
            self.handle_sentence_transe_file_processing(file_path)
            self.move_file(file_path, self.success_dir)
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            self.move_file(file_path, self.failed_dir)

    def handle_sentence_transe_file_processing(self, file_path):
        fixed_columns = ['creator_id', 'creator_name', 'text_content', 'post_date', 'external id']

        file_name, file_extension = os.path.splitext(file_path)
        if file_extension not in ['.xls', '.xlsx']:
            raise InvalidFileException('File extension must be .xls or .xlsx')

        logger.info(f"File updated: {file_path}")

        request_details = extract_request_details_from_file_path(file_path)
        header_df = pd.read_excel(file_path, engine="openpyxl", nrows=1)
        dynamic_columns = header_df.columns[6:]  # Assuming dynamic columns start from the 6th column
        attributes = []
        for col in dynamic_columns:
            if pd.isna(col):  # Skip invalid or empty columns
                logger.debug(f" column is skipping {col}")
                continue
            try:
                # Split the header into attribute_name and type
                attribute_name, attribute_type = col.split('|')
                attributes.append({
                    'attribute_name': attribute_name.strip(),
                    'attribute_type': attribute_type.strip().title()
                })
            except ValueError:
                logger.debug(f"Invalid column format: {col}")

        logger.debug(f"attribute_names={attributes}")
        logger.debug(f"attributes={attributes}")
        if len(attributes) > 0:
            asyncio.run(textset_service.handle_text_set_attributes(attributes, request_details["text_set_id"]))

        logger.debug(f"handle_text_set_attributes continue ")
        total_rows = pd.read_excel(file_path, engine="openpyxl").shape[0]

        chunk_size = config.FILE_CHUNK_SIZE
        if config.FILE_CHUNK_SIZE >= total_rows:
            chunk_size = config.FILE_CHUNK_SIZE
        for start_row in range(0, total_rows, chunk_size):
            logger.debug(f"start_row={start_row} chunk_size={chunk_size}")
            chunk = pd.read_excel(
                file_path,
                engine="openpyxl",
                skiprows=range(1, start_row + 1),  # Skip rows before the current chunk
                nrows=chunk_size,  # Read only the specified number of rows
                header=0  # Assuming the first row contains column headers
            )
            # Process fixed data
            text_content_rows_list = []
            # Process each row
            for index, row in chunk.iterrows():
                attribute_values = {dynamic['attribute_name']: row.get(col, None)
                                    for dynamic, col in zip(attributes, dynamic_columns)
                                    if col in row and not pd.isna(row.get(col, None))  # Skip if the value is NaN
                                    }

                #  logger.debug(f"Row columns: {row.index.tolist()}")
                logger.debug(f" attribute_values : {attribute_values}")

                text_content = row.get('text_content', None)
                post_date_str = row.get('post_date', None)
                logger.debug(f"post_date_str={post_date_str}")
                if post_date_str is None:
                    logger.debug(f"skipping row : {row} because post_date is None.")
                    continue
                post_date = parse_iso8601_date(post_date_str)
                logger.debug(f"post_date={post_date}")
                external_item_id = check_and_replace_nan(row.get('external_item_id', ""))
                parent_external_item_id = check_and_replace_nan(row.get(key='parent_external_item_id', default=" "))
                creator_id = row.get('creator_id', None)
                creator_name = row.get('creator_name', None)
                text_content_row = TextEmbeddingRow(creator_id=creator_id, creator_name=creator_name,
                                                    text_content=text_content, post_date=post_date,
                                                    external_item_id=external_item_id,
                                                    parent_external_item_id=parent_external_item_id,
                                                    embeddings= np.zeros(384).tolist(),
                                                    pca_vector= np.zeros(3).tolist(),
                                                    attributes = attribute_values)
                logger.info(f"class object row : {text_content_row}")
                text_content_rows_list.append(text_content_row)
            logger.debug(f"textContentRowsList {len(text_content_rows_list)}")
            if len(text_content_rows_list) > 0:
                #embedding_rows = handle_embeddings_list(text_content_rows_list)
                #logger.debug(f"embedding_rows={len(embedding_rows)}")
                asyncio.run(textset_service.create_text_sitems(request_details["text_set_id"],text_content_rows_list))


    def move_file(self, file_path, destination_folder):
        """Moves the file to the success or failed folder."""
        try:
            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)  # Create directory if it doesn't exist
            file_name = os.path.basename(file_path)
            destination_path = os.path.join(destination_folder, file_name)
            shutil.move(file_path, destination_path)
            logger.info(f"Moved file {file_path} to {destination_folder}")
        except Exception as e:
            logger.error(f"Error moving file {file_path}: {e}")

    def handle_sentence_transe_file_processing_old(self, file_path):
        file_name, file_extension = os.path.splitext(file_path)
        if file_extension not in ['.xls', '.xlsx']:
            raise InvalidFileException('File extension must be .xls or .xlsx')

        logger.info(f"File updated: {file_path}")

        request_details = extract_request_details_from_file_path(file_path)
        excel = pd.read_excel(file_path, engine="openpyxl", skiprows=0)
        total_rows = excel.shape[0]
        logger.debug(f"total_rows={total_rows}")
        attributes = excel.iloc[0]  # First row (attribute names)

        # logger.debug(f"attribute_names={attributes}")
        logger.debug(f"attributes={attributes}")

        if len(attributes) > 0:
            asyncio.run(textset_service.handle_text_set_attributes(attributes, request_details["text_set_id"]))

        logger.debug(f"handle_text_set_attributes continue ")

        chunk_size = config.FILE_CHUNK_SIZE
        if config.FILE_CHUNK_SIZE >= total_rows:
            chunk_size = config.FILE_CHUNK_SIZE
        for start_row in range(0, total_rows, chunk_size):
            # logger.debug(f"start_row={start_row} chunk_size={chunk_size}")
            df = pd.read_excel(
                file_path,
                engine="openpyxl",
                skiprows=range(1, start_row + 1),  # Skip rows before the current chunk
                nrows=chunk_size,  # Read only the specified number of rows
                header=1  # Assuming the first row contains column headers
            )
            textContentRowsList = []
            for index, row in df.iterrows():
                # logger.debug(f"row= {row}")
                if row.size == 0:
                    logger.warning("Missing line in the row. Skipping.. at index=%s.", index)
                    continue
                text_content = row['text_content']
                post_date_str = row['post_date']
                logger.debug(f"post_date_str={post_date_str}")
                if post_date_str is None:
                    logger.debug(f"skipping row {index}: {row} because post_date is None.")
                    continue
                logger.debug(f"post_date_str={post_date_str}")
                post_date = parse_iso8601_date(post_date_str)
                external_item_id = check_and_replace_nan(row.get('external_item_id', ""))
                parent_external_item_id = check_and_replace_nan(row.get(key='parent_external_item_id', default=" "))
                creator_id = row['creator_id']
                creator_name = row['creator_name']

                attributes_map = {}

                attribute_start_index = 6
                for col_idx, (attribute_name, attribute_value) in enumerate(attributes.items()):  # Enumerate adds the
                    if col_idx < attribute_start_index:
                        continue
                    if not pd.isna(row.iloc[col_idx]):  # Ensure the value is not NaN
                        attributes_map[attribute_name] = row.iloc[col_idx]
                    # logger.debug(f"{col_idx} : attribute_name :{attribute_name} and attribute_value:{row.iloc[col_idx]}")
                logger.debug(f"attributes_map={attributes_map}")

                textContentRow = TextContentRow(creator_id=creator_id, creator_name=creator_name,
                                                text_content=text_content, post_date=post_date,
                                                external_item_id=external_item_id,
                                                parent_external_item_id=parent_external_item_id,
                                                attributes=dict(attributes_map))

                logger.info(f"class object row : {textContentRow}")
                textContentRowsList.append(textContentRow)
            logger.debug(f"textContentRowsList {len(textContentRowsList)} ")
            embedding_rows = handle_embeddings_list(textContentRowsList)
            logger.debug(f"embedding_rows={len(embedding_rows)}")
            asyncio.run(textset_service.create_text_sitems(request_details["text_set_id"], embedding_rows))


def file_processing_worker(queue: Queue, success_dir: str, failed_dir: str):
    """Worker function to process files from the queue."""
    while True:
        file_path = queue.get()  # Get the file from the queue
        if file_path is None:  # None is used as a sentinel value to stop the worker
            break
        logger.info(f"Processing file: {file_path}")
        # Call your file processing function here
        handler = FileObserverHandler(queue, success_dir, failed_dir)  # Create instance
        handler.process_file(file_path)
        queue.task_done()  # Indicate that the file has been processed


def start_file_observer(directory_to_watch, success_dir, failed_dir):
    """Starts the file observer and file processing worker."""
    queue = Queue()

    # Set up the file event handler
    event_handler = FileObserverHandler(queue, success_dir, failed_dir)
    observer = Observer()
    observer.schedule(event_handler, path=directory_to_watch, recursive=False)
    observer.start()
    logger.info(f"Started observing directory: {directory_to_watch}")

    # Start the worker thread to process files from the queue
    worker_thread = threading.Thread(target=file_processing_worker, args=(queue, success_dir, failed_dir))
    worker_thread.daemon = True  # Ensures the worker thread exits when the main program exits
    worker_thread.start()

    # Return the observer and worker thread for proper shutdown
    return observer, worker_thread


def stop_file_observer(observer: Observer, worker_thread: threading.Thread):
    """Stops the file observer and worker thread."""
    observer.stop()
    observer.join()  # Wait for the observer to stop
    # Send a None value to the queue to stop the worker
    worker_thread.join()  # Wait for the worker thread to finish
    logger.info("File observer and worker thread stopped.")
