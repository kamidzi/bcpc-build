import hashlib

# From
# https://github.com/bloomberg/chef-bcpc/blob/30a8971bbc1525a3b3006d6a8729df1f1a22c00b/bootstrap/vagrant_scripts/netid.py
class NetworkIDGenerator:
    @staticmethod
    def generate_id(mapping):
        h = hashlib.sha256()
        for k in sorted(mapping.keys()):
            h.update(str(mapping[k]).encode('utf-8'))
        return h.hexdigest()


if __name__ == '__main__':
# def generate_network_name(label)
#   @vmdir ||=  get_virtualbox_property('default_machine_folder')
#   mapping = {
#     label: label,
#     uid: Process.euid,
#     virtualbox_vm_dir: @vmdir,
#   }
#   @g ||= NetworkIDGenerator.new
#   id = @g.generate_id mapping
#   [label, id].join('-')
# end

    import json

    try:
        mapping_file = sys.argv[1]
    except IndexError:
        sys.exit('Supply a mapping file')

    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
        print(NetworkIDGenerator.generate_id(mapping))

