import os

def clean_files(input_file):
    def replace_commas_nested(text):
        result = []
        stack = []

        for ch in text:
            if ch == "(":
                stack.append(len(result))  # mark start of group
                result.append(ch)
            elif ch == ")":
                if stack:
                    start = stack.pop()
                    # Replace commas inside this group only
                    group = "".join(result[start + 1:])
                    group = group.replace(",", "/")
                    result = result[:start + 1] + list(group)
                result.append(ch)
            else:
                result.append(ch)

        return "".join(result)

    # Step 1: Read file
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    # Step 2: Apply the nested parentheses fix
    fixed_lines = [replace_commas_nested(line) for line in lines]

    # Step 3: Build new filename
    base, ext = os.path.splitext(input_file)
    new_file = f"{base}_issuecleared{ext}"

    print(new_file)
    print("Exists:", os.path.exists(new_file))
    print("Writable:", os.access(os.path.dirname(new_file), os.W_OK))
    # Step 4: Write fixed file
    with open(new_file, 'w', encoding='utf-8', newline='') as outfile:
        outfile.writelines(fixed_lines)

    print(f"Cleaned file written to: {new_file}")
    return new_file


