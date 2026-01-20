from django.shortcuts import render

# Create your views here.


def svg(request):
    username = request.GET.get("username", "")
    if username == "":
        context = {
            "persona_title": "⚠️ 400 Bad Request",
            "status_label": "",
            "comment_line_1": "😵 username is required",
            "comment_line_2": "😱 있어야 할게 없어요",
        }
        return render(request, "card/card.svg", context=context, content_type="image/svg+xml")

    context = {
        "persona_title": "타이틀",
        "status_label": "상태?",
        "comment_line_1": "코멘트1",
        "comment_line_2": "코멘트2",
    }
    return render(request, "card/card.svg", context=context, content_type="image/svg+xml")
