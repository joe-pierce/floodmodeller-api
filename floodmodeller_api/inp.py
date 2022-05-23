'''
Flood Modeller Python API
Copyright (C) 2022 Jacobs U.K. Limited

This program is free software: you can redistribute it and/or modify it under the terms of the GNU ublic License 
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details. 

You should have received a copy of the GNU General Public License along with this program.  If not, see https://www.gnu.org/licenses/.

If you have any query about this program or this License, please contact us at support@floodmodeller.com or write to the following 
address: Jacobs UK Limited, Flood Modeller, Cottons Centre, Cottons Lane, London, SE1 2QG, United Kingdom.
'''
from pathlib import Path
from typing import Optional, Union
from floodmodeller_api.urban1d import subsections
from floodmodeller_api.urban1d.general_parameters import DEFAULT_OPTIONS
from ._base import FMFile
from . import units
class INP(FMFile):
    """Reads and writes Flood Modeller 1DUrban file format '.inp'

    Args:
        inp_filepath (str, optional): Full filepath to inp file. If not specified, a new INP class will be created. Defaults to None. 

    Output:
        Initiates 'INP' class object

    Raises:
        TypeError: Raised if inp_filepath does not point to a .inp file
        FileNotFoundError: Raised if inp_filepath points to a file which does not exist
    """

    _filetype: str = 'INP'
    _suffix:str = '.inp'
    

    def __init__(self, inp_filepath: Optional[Union[str, Path]] = None):
        self._filepath = inp_filepath  
        if self._filepath != None:
            FMFile.__init__(self)
            self._read()
        
        else:
            self._create_from_blank()
            
        self._get_section_definitions()

    def _read(self):
        # Read INP file
        with open(self._filepath, 'r') as inp_file:
            self._raw_data = [line.rstrip('\n')
                              for line in inp_file.readlines()]

        # Generate INP file structure
        self._update_inp_struct() 
        

    def _write(self) -> str:
        """Returns string representation of the current INP data

        Returns:
            str: Full string representation of INP in its most recent state (including changes not yet saved to disk)
        """
        
        block_shift = 0 # Used to allow changes in the length of subsections.
        # existing_units = {'junctions': [], 'raingauges': []} MAYBE REQUIRED

        for block in self._inp_struct:
            if block['Subsection_Type'] in subsections.SUPPORTED_SUBSECTIONS:
                subsection_data = self._raw_data[block['start'] + block_shift: block['end'] + 1 + block_shift]
                prev_block_len = len(subsection_data)
                
                subsection = getattr(self, subsections.SUPPORTED_SUBSECTIONS[block['Subsection_Type']]['attribute']) # Get unit object
                new_subsection_data = subsection._write() # String representation of unit object

                #TODO: add functionality to update name.  see DAT as example, and commented out code in here

                new_block_len = len(new_subsection_data)

                self._raw_data[block['start'] + block_shift: block['end'] + 1 + block_shift] = new_subsection_data # Replace existing subsection with new subsection string 
                block_shift += (new_block_len - prev_block_len) # adjust block shift for change in number of lines in block

        # TODO: Add functionality to update general parameters - update raw data directly.

        # Regenerate INP file structure
        self._update_inp_struct()    

        #EXAMPLE
        # for unit_group in [self.boundaries, self.sections, self.structures]:
        #     for name, unit in unit_group.copy().items():
        #         if name != unit.name:
        #             unit_group[unit.name] = unit
        #             del unit_group[name]
        #             # Update label in ICs
        #             self.initial_conditions.update_label(name, unit.name)



        # Write _raw_data out to INP file. 
        inp_string = ''
        for line in self._raw_data:
            inp_string += line + '\n'

        '\n'.join(self._raw_data)

        return inp_string

    def _create_from_blank(self):
        pass
    
    def _get_section_definitions(self):
        """Internal method used to get section definitions for each supported unit type and general parameters."""

        # Loop through all blocks (subsections) within INP  and process if of a supported type.
        for block in self._inp_struct:             
            if block['Subsection_Type'] in subsections.SUPPORTED_SUBSECTIONS: 
                
                raw_subsection_data = self._raw_data[block['start']: block['end'] + 1] # Raw data for subsection block of INP file

                # Check if subsection type is 'general' and therefore is stored as attribute of INP class
                if subsections.SUPPORTED_SUBSECTIONS[block['Subsection_Type']]['group'] == 'general': 
                    
                    if block['Subsection_Type'] == '[OPTIONS]':
                        self.options = DEFAULT_OPTIONS.copy()  
                        self._option_order = [] 
                        for  line in raw_subsection_data:                          
                            if line.upper() not in subsections.SUPPORTED_SUBSECTIONS and line.strip() != "" and not line.startswith(';'):
                                data = units.helpers.split_n_char(line, 21)
                                
                                self.options[data[0].lower()] = data[1]
                                self._option_order.append(data[0])
               
                # Create appropriate sub-class instences for supported units
                elif subsections.SUPPORTED_SUBSECTIONS[block['Subsection_Type']]['group'] == 'units':   
                    subsection_class = subsections.SUPPORTED_SUBSECTIONS[block['Subsection_Type']]['class']
                    subsection_attribute = subsections.SUPPORTED_SUBSECTIONS[block['Subsection_Type']]['attribute']

                    setattr(self, subsection_attribute, subsection_class(raw_subsection_data)) 
                    subsection = getattr(self,subsection_attribute)                  
                    subsection_units = getattr(subsection, subsection._attribute)
                    setattr(self, subsection._attribute,subsection_units)


                # No action if subsection not supported. Leave block as raw data

    def _update_inp_struct(self): 
        """Internal method used to update self._inp_struct which details the overall structure of the inp file as a list of blocks, each of which
            are a dictionary containing the 'start', 'end' and 'type' of the block.

        """
        # Generate INP file structure
        inp_struct = []
        in_block = False
        unit_block = {}
        for idx, line in enumerate(self._raw_data):
            
            #TODO: Add functionality to compare first four characters only (alphanumeric) - need to consider names shorter than 4 characters, and those with _ within name
            
            # Check if subsection is known 
            if line.upper() in subsections.ALL_SUBSECTIONS: 

                if in_block == True:
                    unit_block['end'] = idx - 1  # add ending index
                    inp_struct.append(unit_block) # append existing block bdy to the inp_struct
                    unit_block = {}  # reset bdy block

                unit_block['Subsection_Type'] = line.upper()
                unit_block['start'] = idx
                in_block = True

        if len(unit_block) != 0:
            # Only adds end block if there is a block present (i.e. an empty inp stays empty)
            # add ending index for final block
            unit_block['end'] = len(self._raw_data) - 1
            inp_struct.append(unit_block)  # add final block

        self._inp_struct = inp_struct

    def update(self) -> None:
        """ Updates the existing INP based on any altered attributes """
        
        self._update()

    def save(self, filepath: Union[str, Path]) -> None:
        """Saves the INP to the given location, if pointing to an existing file it will be overwritten. 
        Once saved, the INP() class will continue working from the saved location, therefore any further calls to INP.update() will 
        update in the latest saved location rather than the original source INP used to construct the class

        Args:
            filepath (str): Filepath to new save location including the name and '.inp' extension

        Raises:
            TypeError: Raised if given filepath doesn't point to a file suffixed '.inp'

        """

        filepath = Path(filepath).absolute()
        self._save(filepath)

