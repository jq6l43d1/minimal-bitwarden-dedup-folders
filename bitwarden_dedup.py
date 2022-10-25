import json

# Your RAM disk file paths here
VAULT_WITH_DUPS_PATH = "/mnt/ramdisk/my_bitwarden_export.json"
VAULT_DEDUPED_OUTPUT_PATH = "/mnt/ramdisk/my_unencrypted_deduped_bitwarden_export.json"


def dedup(vault_with_dups_path, vault_deduped_output_path, paranoid=True):
    with open(vault_with_dups_path, encoding='utf-8', mode='r') as vaultfile:
        vault_json = json.load(vaultfile)

    assert not vault_json["encrypted"], """Unfortunately you need to export your vault unencrypted.
    BitWarden seems to use a login item's unique id as salt (or something like that), so there would
    be no duplicates in the encrypted file."""

    items = vault_json["items"]

    # use a set to detect duplicates.
    # two json item objects are duplicates if and only if, after their "id" and "folderId" keys are removed, they
    # have the same string representations (same value of json.dumps).
    item_identities = set()

    # will be the new contents of the "items" map
    deduped_items = []

    for item in items:
        item_id = item["id"]
        folder_id = item["folderId"]
        # delete id and folderId since they're the two things that are different in otherwise-exact duplicate items
        # rather than `del` them, just set them to "", since otherwise they moves the key in the ordered dict, which results
        # in a different ordering in the json output.
        item["id"] = ""
        item["folderId"] = ""
        item_identity = json.dumps(item)
        if item_identity not in item_identities:
            item_identities.add(item_identity)
            # add the id and the folder ID back
            item["id"] = item_id
            item["folderId"] = folder_id
            deduped_items.append(item)

    vault_json["items"] = deduped_items

    print(f"{len(items) - len(item_identities)} duplicates removed.")
    print(
        f"Exported file has {len(item_identities)} login/password/secret items.")

    # Folder deduplication
    original_folders = vault_json["folders"]

    items = vault_json["items"]
    folders = vault_json["folders"]

    folder_identities = set()

    deduped_folders = []
    deduped_items = []

    for folder in folders:
        folder_id = folder["id"]

        folder["id"] = ""
        folder_identity = json.dumps(folder)
        if folder_identity not in folder_identities:
            folder_identities.add(folder_identity)

            folder["id"] = folder_id
            deduped_folders.append(folder)
        else:
            # Get deduped folderId
            for deduped_folder in deduped_folders:
                if deduped_folder["name"] == folder["name"]:
                    deduped_folderId = deduped_folder["id"]
                    break

            # Change folderIds to the deduped one
            for item in items:
                if item["folderId"] == folder_id:
                    item["folderId"] = deduped_folderId

    vault_json["folders"] = deduped_folders
    vault_json["items"] = items

    # Prune empty folders
    items = vault_json["items"]
    folders = vault_json["folders"]
    inuse_folders = []

    folders = vault_json["folders"]
    for folder in folders:
        folder_id = folder["id"]
        for item in items:
            if item["folderId"] == folder_id:
                inuse_folders.append(folder)
                break

    vault_json["folders"] = inuse_folders

    print(f"{len(original_folders) - len(inuse_folders)} duplicate or empty folders removed.")
    print(f"Exported file has {len(inuse_folders)} folders.")

    with open(vault_deduped_output_path, encoding='utf-8', mode='w') as newvaultfile:
        # need ensure_ascii=False because bitwarden doesn't escape unicode characters
        json.dump(vault_json, newvaultfile, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    dedup(VAULT_WITH_DUPS_PATH, VAULT_DEDUPED_OUTPUT_PATH)

