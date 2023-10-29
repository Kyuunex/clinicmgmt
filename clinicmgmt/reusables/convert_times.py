def str_to_seconds(offset_str):
    hours = int(f"{offset_str[1]}{offset_str[2]}")
    minutes = int(f"{offset_str[4]}{offset_str[5]}")
    total_seconds = hours * 60 * 60 + minutes * 60

    if offset_str[0] == "-":
        final = total_seconds * (-1)
    elif offset_str[0] == "+":
        final = total_seconds
    else:
        return 0

    return final
