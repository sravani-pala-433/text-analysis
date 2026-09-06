from sqlalchemy.types import UserDefinedType
import numpy as np


class VectorType(UserDefinedType):
	def __init__(self, size: int):
		self.size = size  # Store the size dynamically
	
	def get_col_spec(self):
		return f"VECTOR({self.size})"  # Return the VECTOR(size)
	
	def bind_expression(self, value):
		return value  # Handle any necessary bindings
	
	def column_expression(self, col):
		return col  # Handle any necessary column-level expressions
	
	def bind_processor(self, dialect):
	
		def process(value):
			if value is not None:
				# Ensure the value is a list of floats (or numpy array)
				if isinstance(value, np.ndarray):
					return value.tolist()  # Ensure it's a list
				elif isinstance(value, list):
					# Make sure all elements in the list are floats
					return [float(v) for v in value]
				else:
					raise ValueError("Value must be a list or numpy array of floats.")
			return value
		
		return process
	
	def result_processor(self, dialect, coltype):
		"""
		Convert the value coming back from the database into a list of floats.
		This is the reverse of the bind processor.
		"""
		
		def process(value):
			if value is not None:
				# Ensure the result is returned as a list of floats
				if isinstance(value, str):
					# If the value is a string (which means it was stored incorrectly),
					# safely evaluate it and convert to a list
					try:
						value = eval(value)  # Convert string to list
					except Exception as e:
						raise ValueError(f"Error evaluating value: {e}")
				
				# Ensure it's a list of floats
				return [float(v) for v in value]
			return value
		
		return process
	
	def bind_processor1(self, dialect):
		def process(value):
			if value is not None:
				return list(value)  # Ensure it's a list
			return value
		
		return process
	
	def result_processor1(self, dialect, coltype):
		def process(value):
			if value is not None:
				print(f" value result {value} {type(value)} ")
				return value  # Ensure result is a list
			return value
		
		return process
