from django.shortcuts import render

# Create your views here.


def svg(request):
    context = {
        "persona_title": "111",
        "status_label": "222",
        "comment_line_1": "333",
        "comment_line_2": "444",
    }
    return render(request, "card/card.svg", context=context, content_type="image/svg+xml")
