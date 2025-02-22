import requests
import io
import bpy
import numpy as np
from . import coll
import warnings
from . import data
from . import assembly
from . import nodes

def molecule_rcsb(
    pdb_code,               
    center_molecule = False,               
    del_solvent = True,               
    include_bonds = True,   
    starting_style = 0,               
    setup_nodes = True              
    ):
    mol, file = open_structure_rcsb(
        pdb_code = pdb_code, 
        include_bonds=include_bonds
        )
    
    mol_object, coll_frames = create_molecule(
        mol_array = mol,
        mol_name = pdb_code,
        file = file,
        calculate_ss = False,
        center_molecule = center_molecule,
        del_solvent = del_solvent, 
        include_bonds = include_bonds
        )
    
    if setup_nodes:
        nodes.create_starting_node_tree(
            obj = mol_object, 
            coll_frames=coll_frames, 
            starting_style = starting_style
            )
    
    mol_object['bio_transform_dict'] = file['bioAssemblyList']
    
    return mol_object

def molecule_esmfold(
    amino_acid_sequence,               
    mol_name = "Name",                   
    center_molecule = False,               
    del_solvent = True,               
    include_bonds = True,   
    starting_style = 0,               
    setup_nodes = True              
    ):
    mol, file = open_structure_esm_fold(
        amino_acid_sequence = amino_acid_sequence, 
        include_bonds=include_bonds
        )
    
    mol_object, coll_frames = create_molecule(
        mol_array = mol,
        mol_name = mol_name,
        file = file,
        calculate_ss = True,
        center_molecule = center_molecule,
        del_solvent = del_solvent, 
        include_bonds = True
        )
    
    if setup_nodes:
        nodes.create_starting_node_tree(
            obj = mol_object, 
            coll_frames=coll_frames, 
            starting_style = starting_style
            )    
    return mol_object

def molecule_local(
    file_path,                    
    mol_name = "Name",                   
    include_bonds = True,                    
    center_molecule = False,                    
    del_solvent = True,                    
    default_style = 0,                    
    setup_nodes = True
    ): 
    
    import biotite.structure as struc
    import os
    
    file_path = os.path.abspath(file_path)
    file_ext = os.path.splitext(file_path)[1]
    
    if file_ext == '.pdb':
        mol, file = open_structure_local_pdb(file_path, include_bonds)
        transforms = assembly.get_transformations_pdb(file)
    elif file_ext == '.pdbx' or file_ext == '.cif':
        mol, file = open_structure_local_pdbx(file_path, include_bonds)
        try:
            transforms = assembly.get_transformations_pdbx(file)
        except:
            transforms = None
            # self.report({"WARNING"}, message='Unable to parse biological assembly information.')
    else:
        warnings.warn("Unable to open local file. Format not supported.")
    # if include_bonds chosen but no bonds currently exist (mol.bonds is None)
    # then attempt to find bonds by distance
    if include_bonds and not mol.bonds:
        mol.bonds = struc.connect_via_distances(mol[0], inter_residue=True)
    
    if not (file_ext == '.pdb' and file.get_model_count() > 1):
        file = None
        
    
    mol_object, coll_frames = create_molecule(
        mol_array = mol,
        mol_name = mol_name,
        file = file,
        calculate_ss = True,
        center_molecule = center_molecule,
        del_solvent = del_solvent, 
        include_bonds = include_bonds
        )
    
    # setup the required initial node tree on the object 
    if setup_nodes:
        nodes.create_starting_node_tree(
            obj = mol_object,
            coll_frames = coll_frames,
            starting_style = default_style
            )
    
    # if transforms:
        # mol_object['bio_transform_dict'] = (transforms)
        # mol_object['bio_transnform_dict'] = 'testing'
        
    return mol_object


def open_structure_rcsb(pdb_code, include_bonds = True):
    import biotite.structure.io.mmtf as mmtf
    import biotite.database.rcsb as rcsb
    
    file = mmtf.MMTFFile.read(rcsb.fetch(pdb_code, "mmtf"))
    
    # returns a numpy array stack, where each array in the stack is a model in the 
    # the file. The stack will be of length = 1 if there is only one model in the file
    mol = mmtf.get_structure(file, extra_fields = ["b_factor", "charge"], include_bonds = include_bonds) 
    return mol, file

def open_structure_esm_fold(amino_acid_sequence, include_bonds=True):
    import biotite.structure.io.pdb as pdb
    
    
    
    # output_of_subprocess = subprocess.Popen([
    # 'curl',
    # '-X',
    # 'POST',
    # '--data',
    # amino_acid_sequence,
    # 'https://api.esmatlas.com/foldSequence/v1/pdb/'
    # ], stdout=subprocess.PIPE)

    # (esm_folded_pdb_str, err) = output_of_subprocess.communicate()

    r = requests.post('https://api.esmatlas.com/foldSequence/v1/pdb/', data=amino_acid_sequence)
    
    if r.ok:
    
        esm_folded_pdb_str = r.text
        with io.StringIO() as f:
            f.write(esm_folded_pdb_str)
            f.seek(0)
            file = pdb.PDBFile.read(f)
    
        # returns a numpy array stack, where each array in the stack is a model in the 
        # the file. The stack will be of length = 1 if there is only one model in the file
        mol = pdb.get_structure(file, extra_fields = ['b_factor', 'charge'], include_bonds = include_bonds)
        return mol, file

    else:
        raise ValueError(f'ESMFold returned an error for the amino acid sequence input. This is the error message: {r.text}')
    
def open_structure_local_pdb(file_path, include_bonds = True):
    import biotite.structure.io.pdb as pdb
    
    file = pdb.PDBFile.read(file_path)
    
    # returns a numpy array stack, where each array in the stack is a model in the 
    # the file. The stack will be of length = 1 if there is only one model in the file
    mol = pdb.get_structure(file, extra_fields = ['b_factor', 'charge'], include_bonds = include_bonds)
    return mol, file

def open_structure_local_pdbx(file_path, include_bonds = True):
    import biotite.structure as struc
    import biotite.structure.io.pdbx as pdbx
    
    file = pdbx.PDBxFile.read(file_path)
    
    # returns a numpy array stack, where each array in the stack is a model in the 
    # the file. The stack will be of length = 1 if there is only one model in the file
    mol  = pdbx.get_structure(file, extra_fields = ['b_factor', 'charge'])
    # pdbx doesn't include bond information apparently, so manually create
    # them here if requested
    if include_bonds:
        mol[0].bonds = struc.bonds.connect_via_residue_names(mol[0], inter_residue = True)
    return mol, file

def create_object(name, collection, locations, bonds=[]):
    """
    Creates a mesh with the given name in the given collection, from the supplied
    values for the locations of vertices, and if supplied, bonds as edges.
    """
    # create a new mesh
    mol_mesh = bpy.data.meshes.new(name)
    mol_mesh.from_pydata(locations, bonds, faces=[])
    mol_object = bpy.data.objects.new(name, mol_mesh)
    collection.objects.link(mol_object)
    return mol_object

def add_attribute(object, name, data, type = "FLOAT", domain = "POINT", add = True):
    if not add:
        return None
    attribute = object.data.attributes.new(name, type, domain)
    attribute.data.foreach_set('value', data)

def pdb_get_b_factors(file):
    """
    Get a list, which contains a numpy array for each model containing the b-factors.
    """
    b_factors = []
    for model in range(file.get_model_count()):
        atoms = file.get_structure(model = model + 1, extra_fields = ['b_factor'])
        b_factors.append(atoms.b_factor)
    return b_factors

def get_secondary_structure(mol_array, file) -> np.array:
    """
    Gets the secondary structure annotation that is included in mmtf files and returns it as a numerical numpy array.

    Parameters:
    -----------
    mol_array : numpy.array
        The molecular coordinates array, from mmtf.get_structure()
    file : mmtf.MMTFFile
        The MMTF file containing the secondary structure information, from mmtf.MMTFFile.read()

    Returns:
    --------
    atom_sse : numpy.array
        Numerical numpy array representing the secondary structure of the molecule.
    
    Description:
    ------------
    This function uses the biotite.structure package to extract the secondary structure information from the MMTF file.
    The resulting secondary structures are `1: Alpha Helix, 2: Beta-sheet, 3: loop`.
    """
    
    from biotite.structure import spread_residue_wise
    
    sec_struct_codes = {
        -1: "X",
        0 : "I",
        1 : "S",
        2 : "H",
        3 : "E",
        4 : "G",
        5 : "B",
        6 : "T",
        7 : "C"
    }
    
    dssp_to_abc = {
        "X" : 0,
        "I" : 1, #"a",
        "S" : 3, #"c",
        "H" : 1, #"a",
        "E" : 2, #"b",
        "G" : 1, #"a",
        "B" : 2, #"b",
        "T" : 3, #"c",
        "C" : 3 #"c"
    }
    
    try:
        sse = file["secStructList"]
    except KeyError:
        ss_int = np.full(len(mol_array), 3)
        print('Warning: "secStructList" field missing from MMTF file. Defaulting \
            to "loop" for all residues.')
    else:
        ss_int = np.array(
            [dssp_to_abc.get(sec_struct_codes.get(ss)) for ss in sse], 
            dtype = int
        )
    atom_sse = spread_residue_wise(mol_array, ss_int)
    
    return atom_sse


def comp_secondary_structure(mol_array):
    """Use dihedrals to compute the secondary structure of proteins

    Through biotite built-in method derivated from P-SEA algorithm (Labesse 1997)
    Returns an array with secondary structure for each atoms where:
    - 0 = '' = non-protein or not assigned by biotite annotate_sse
    - 1 = a = alpha helix
    - 2 = b = beta sheet
    - 3 = c = coil

    Inspired from https://www.biotite-python.org/examples/gallery/structure/transketolase_sse.html
    """
    #TODO Port [PyDSSP](https://github.com/ShintaroMinami/PyDSSP)
    #TODO Read 'secStructList' field from mmtf files
    from biotite.structure import annotate_sse, spread_residue_wise

    conv_sse_char_int = {'a': 1, 'b': 2, 'c': 3, '': 0} 

    char_sse = annotate_sse(mol_array)
    int_sse = np.array([conv_sse_char_int[char] for char in char_sse], dtype=int)
    atom_sse = spread_residue_wise(mol_array, int_sse)
        
    return atom_sse

def create_molecule(mol_array, 
                    mol_name, 
                    center_molecule = False, 
                    file = None,
                    calculate_ss = False,
                    del_solvent = False, 
                    include_bonds = False, 
                    collection = None
                    ):
    import biotite.structure as struc
    
    if np.shape(mol_array)[0] > 1:
        mol_frames = mol_array
    else:
        mol_frames = None
    
    mol_array = mol_array[0]
    
    # remove the solvent from the structure if requested
    if del_solvent:
        mol_array = mol_array[np.invert(struc.filter_solvent(mol_array))]

    world_scale = 0.01
    locations = mol_array.coord * world_scale
    
    centroid = np.array([0, 0, 0])
    if center_molecule:
        centroid = struc.centroid(mol_array) * world_scale
    

    # subtract the centroid from all of the positions to localise the molecule on the world origin
    if center_molecule:
        locations = locations - centroid

    if not collection:
        collection = coll.mn()
    
    if include_bonds and mol_array.bonds:
        bonds = mol_array.bonds.as_array()
        mol_object = create_object(name = mol_name, collection = collection, locations = locations, bonds = bonds[:, [0,1]])
    else:
        mol_object = create_object(name = mol_name, collection = collection, locations = locations)

    # The attributes for the model are initially defined as single-use functions. This allows
    # for a loop that attempts to add each attibute by calling the function. Only during this
    # loop will the call fail if the attribute isn't accessible, and the warning is reported
    # there rather than setting up a try: except: for each individual attribute which makes
    # some really messy code.
    
    # I still don't like this as an implementation, and welcome any cleaner approaches that 
    # anybody might have.
    
    def att_atomic_number():
        atomic_number = np.array(list(map(
            lambda x: data.elements.get(x, {'atomic_number': -1}).get("atomic_number"), 
            np.char.title(mol_array.element))))
        return atomic_number
    
    def att_res_id():
        return mol_array.res_id
    
    def att_res_name():
        other_res = []
        counter = 0
        id_counter = -1
        res_names = mol_array.res_name
        res_names_new = []
        res_ids = mol_array.res_id
        res_nums  = []
        
        for name in res_names:
            res_num = data.residues.get(name, {'res_name_num': 9999}).get('res_name_num')
            
            if res_num == 9999:
                if res_names[counter - 1] != name or res_ids[counter] != res_ids[counter - 1]:
                    id_counter += 1
                
                unique_res_name = str(id_counter + 100) + "_" + str(name)
                other_res.append(unique_res_name)
                
                num = np.where(np.isin(np.unique(other_res), unique_res_name))[0][0] + 100
                res_nums.append(num)
            else:
                res_nums.append(res_num)
            counter += 1

        mol_object['ligands'] = np.unique(other_res)
        return np.array(res_nums)

    
    def att_chain_id():
        chain_id = np.searchsorted(np.unique(mol_array.chain_id), mol_array.chain_id)
        return chain_id
    
    def att_b_factor():
        return mol_array.b_factor
    
    def att_vdw_radii():
        vdw_radii =  np.array(list(map(
            # divide by 100 to convert from picometres to angstroms which is what all of coordinates are in
            lambda x: data.elements.get(x, {'vdw_radii': 100}).get('vdw_radii', 100) / 100,  
            np.char.title(mol_array.element)
            )))
        return vdw_radii * world_scale
    
    def att_atom_name():
        atom_name = np.array(list(map(
            lambda x: data.atom_names.get(x, 9999), 
            mol_array.atom_name
        )))
        
        return atom_name
    
    def att_is_alpha():
        return np.isin(mol_array.atom_name, 'CA')
    
    def att_is_solvent():
        return struc.filter_solvent(mol_array)
    
    def att_is_backbone():
        is_backbone = (struc.filter_backbone(mol_array) | 
                        np.isin(mol_array.atom_name, ["P", "O5'", "C5'", "C4'", "C3'", "O3'"]))
        return is_backbone
    
    def att_is_nucleic():
        return struc.filter_nucleotides(mol_array)
    
    def att_is_peptide():
        aa = struc.filter_amino_acids(mol_array)
        con_aa = struc.filter_canonical_amino_acids(mol_array)
        
        return aa | con_aa
    
    def att_is_hetero():
        return mol_array.hetero
    
    def att_is_carb():
        return struc.filter_carbohydrates(mol_array)

    def att_sec_struct():
        if calculate_ss or not file:
            return comp_secondary_structure(mol_array)
        else:
            return get_secondary_structure(mol_array, file)
    

    # Add information about the bond types to the model on the edge domain
    # Bond types: 'ANY' = 0, 'SINGLE' = 1, 'DOUBLE' = 2, 'TRIPLE' = 3, 'QUADRUPLE' = 4
    # 'AROMATIC_SINGLE' = 5, 'AROMATIC_DOUBLE' = 6, 'AROMATIC_TRIPLE' = 7
    # https://www.biotite-python.org/apidoc/biotite.structure.BondType.html#biotite.structure.BondType
    if include_bonds:
        try:
            add_attribute(
                object = mol_object, 
                name = 'bond_type', 
                data = bonds[:, 2].copy(order = 'C'), # the .copy(order = 'C') is to fix a weird ordering issue with the resulting array
                type = "INT", 
                domain = "EDGE"
                )
        except:
            warnings.warn('Unable to add bond types to the molecule.')

    
    # these are all of the attributes that will be added to the structure
    # TODO add capcity for selection of particular attributes to include / not include to potentially
    # boost performance, unsure if actually a good idea of not. Need to do some testing.
    attributes = (
        {'name': 'res_id',          'value': att_res_id,              'type': 'INT',     'domain': 'POINT'},
        {'name': 'res_name',        'value': att_res_name,            'type': 'INT',     'domain': 'POINT'},
        {'name': 'atomic_number',   'value': att_atomic_number,       'type': 'INT',     'domain': 'POINT'},
        {'name': 'b_factor',        'value': att_b_factor,            'type': 'FLOAT',   'domain': 'POINT'},
        {'name': 'vdw_radii',       'value': att_vdw_radii,           'type': 'FLOAT',   'domain': 'POINT'},
        {'name': 'chain_id',        'value': att_chain_id,            'type': 'INT',     'domain': 'POINT'},
        {'name': 'atom_name',       'value': att_atom_name,           'type': 'INT',     'domain': 'POINT'},
        {'name': 'is_backbone',     'value': att_is_backbone,         'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'is_alpha_carbon', 'value': att_is_alpha,            'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'is_solvent',      'value': att_is_solvent,          'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'is_nucleic',      'value': att_is_nucleic,          'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'is_peptide',      'value': att_is_peptide,          'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'is_hetero',       'value': att_is_hetero,           'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'is_carb',         'value': att_is_carb,             'type': 'BOOLEAN', 'domain': 'POINT'},
        {'name': 'sec_struct',      'value': att_sec_struct,          'type': 'INT',     'domain': 'POINT'}
    )
    
    # assign the attributes to the object
    for att in attributes:
        # try:
        add_attribute(mol_object, att['name'], att['value'](), att['type'], att['domain'])
        # except:
            # warnings.warn(f"Unable to add attribute: {att['name']}")

    if mol_frames:
        try:
            b_factors = pdb_get_b_factors(file)
        except:
            b_factors = None
        
        coll_frames = coll.frames(mol_object.name)
        
        for i, frame in enumerate(mol_frames):
            obj_frame = create_object(
                name = mol_object.name + '_frame_' + str(i), 
                collection=coll_frames, 
                locations= frame.coord * world_scale - centroid
            )
            if b_factors:
                try:
                    add_attribute(obj_frame, 'b_factor', b_factors[i])
                except:
                    b_factors = False
        
        # disable the frames collection so it is not seen
        bpy.context.view_layer.layer_collection.children[collection.name].children[coll_frames.name].exclude = True
    else:
        coll_frames = None
    
    # add custom properties to the actual blender object, such as number of chains, biological assemblies etc
    # currently biological assemblies can be problematic to holding off on doing that
    try:
        mol_object['chain_id_unique'] = list(np.unique(mol_array.chain_id))
    except:
        warnings.warn('No chain information detected.')
    
    return mol_object, coll_frames


def load_star_file(
    file_path, 
    obj_name = 'NewStarInstances', 
    node_tree = True,
    world_scale =  0.01 
    ):
    import starfile
    from eulerangles import ConversionMeta, convert_eulers
    
    star = starfile.read(file_path, always_dict=True)
    
    star_type = None
    # only RELION 3.1 and cisTEM STAR files are currently supported, fail gracefully
    if 'particles' in star and 'optics' in star:
        star_type = 'relion'
    elif "cisTEMAnglePsi" in star[0]:
        star_type = 'cistem'
    else:
        raise ValueError(
        'File is not a valid RELION>=3.1 or cisTEM STAR file, other formats are not currently supported.'
        )
    
    # Get absolute position and orientations    
    if star_type == 'relion':
        df = star['particles'].merge(star['optics'], on='rlnOpticsGroup')

        # get necessary info from dataframes
        # Standard cryoEM starfile don't have rlnCoordinateZ. If this column is not present 
        # Set it to "0"
        if "rlnCoordinateZ" not in df:
            df['rlnCoordinateZ'] = 0
            
        xyz = df[['rlnCoordinateX', 'rlnCoordinateY', 'rlnCoordinateZ']].to_numpy()
        pixel_size = df['rlnImagePixelSize'].to_numpy().reshape((-1, 1))
        xyz *= pixel_size
        shift_column_names = ['rlnOriginXAngst', 'rlnOriginYAngst', 'rlnOriginZAngst']
        if all([col in df.columns for col in shift_column_names]):
            shifts_ang = df[shift_column_names].to_numpy()
            xyz -= shifts_ang 
        euler_angles = df[['rlnAngleRot', 'rlnAngleTilt', 'rlnAnglePsi']].to_numpy()
        image_id = df['rlnMicrographName'].astype('category').cat.codes.to_numpy()
        
    elif star_type == 'cistem':
        df = star[0]
        df['cisTEMZFromDefocus'] = (df['cisTEMDefocus1'] + df['cisTEMDefocus2']) / 2
        df['cisTEMZFromDefocus'] = df['cisTEMZFromDefocus'] - df['cisTEMZFromDefocus'].median()
        xyz = df[['cisTEMOriginalXPosition', 'cisTEMOriginalYPosition', 'cisTEMZFromDefocus']].to_numpy()
        euler_angles = df[['cisTEMAnglePhi', 'cisTEMAngleTheta', 'cisTEMAnglePsi']].to_numpy()
        image_id = df['cisTEMOriginalImageFilename'].astype('category').cat.codes.to_numpy()

    # coerce starfile Euler angles to Blender convention
    
    target_metadata = ConversionMeta(name='output', 
                                    axes='xyz', 
                                    intrinsic=False,
                                    right_handed_rotation=True,
                                    active=True)
    eulers = np.deg2rad(convert_eulers(euler_angles, 
                               source_meta='relion', 
                               target_meta=target_metadata))

    obj = create_object(obj_name, coll.mn(), xyz * world_scale)
    
    # vectors have to be added as a 1D array currently
    rotations = eulers.reshape(len(eulers) * 3)
    # create the attribute and add the data for the rotations
    attribute = obj.data.attributes.new('MOLRotation', 'FLOAT_VECTOR', 'POINT')
    attribute.data.foreach_set('vector', rotations)

    # create the attribute and add the data for the image id
    attribute_imgid = obj.data.attributes.new('MOLImageId', 'INT', 'POINT')
    attribute_imgid.data.foreach_set('value', image_id)
    # create attribute for every column in the STAR file
    for col in df.columns:
        col_type = df[col].dtype
        # If col_type is numeric directly add
        if np.issubdtype(col_type, np.number):
            attribute = obj.data.attributes.new(col, 'FLOAT', 'POINT')
            attribute.data.foreach_set('value', df[col].to_numpy().reshape(-1))
        # If col_type is object, convert to category and add integer values
        elif col_type == np.object:
            attribute = obj.data.attributes.new(col, 'INT', 'POINT')
            codes = df[col].astype('category').cat.codes
            attribute.data.foreach_set('value', codes.to_numpy().reshape(-1))
            # Add the category names as a property to the blender object
            obj[col + '_categories'] = list(df[col].astype('category').cat.categories)
    
    if node_tree:
        nodes.create_starting_nodes_starfile(obj)
    
    return obj
    