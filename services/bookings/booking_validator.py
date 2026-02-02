def validate_passengers(passengers: list, age: int):
    adults = []
    children = []
    infants = []
    for idx, p in enumerate(passengers):
        p_type = p.type

        # 🔒 Enforce age ↔ type consistency
        if age >= 16:
            if p_type != "adult":
                raise ValueError(f"Passenger '{p.name}' must be adult (age ≥ 16)")
            adults.append(idx)

            if not p.email or not p.phone:
                raise ValueError("Adult passengers must have email and phone")

        elif 6 < age < 16:
            if p_type != "child":
                raise ValueError(f"Passenger '{p.name}' must be child (age 7–15)")
            children.append(idx)

        elif age <= 6:
            if p_type != "infant":
                raise ValueError(f"Passenger '{p.name}' must be infant (age ≤ 6)")
            infants.append(idx)

        else:
            raise ValueError("Invalid passenger age")

    # 🔒 Global rules
    if len(adults) < 1:
        raise ValueError("At least one adult (age ≥ 16) is required")

    if len(infants) > len(adults):
        raise ValueError("Infants cannot exceed adults")

    # 🔒 Guardian enforcement
    for idx in children + infants:
        guardian_index = passengers[idx].guardian_index

        if guardian_index is None:
            raise ValueError("Child/Infant must have a guardian")

        if guardian_index not in adults:
            raise ValueError("Guardian must be an adult (age ≥ 16)")

    return {
        "adults": len(adults),
        "children": len(children),
        "infants": len(infants),
        "adult_indexes": adults
    }
