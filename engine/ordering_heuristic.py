def course_sort_key(course):
    """Descending enrolment, descending credits, then course code."""
    return (
        -int(course.get("enrolment_count", 0)),
        -int(course.get("credits", 0)),
        course["course_code"],
    )

def order_courses(courses):
    return sorted(courses, key=course_sort_key)
